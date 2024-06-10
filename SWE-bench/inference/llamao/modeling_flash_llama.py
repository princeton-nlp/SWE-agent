# Copyright 2022 EleutherAI and the HuggingFace Inc. team. All rights reserved.
#
# This code is based on EleutherAI's GPT-NeoX library and the GPT-NeoX
# and OPT implementations in this library. It has been modified from its
# original forms to accommodate minor architectural differences compared
# to GPT-NeoX and OPT used by the Meta AI team that trained the model.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" PyTorch LLaMA model."""
from typing import Optional, Union, Any

import torch
import torch.nn.functional as F
import torch.utils.checkpoint
from torch import nn
from torch.nn import BCEWithLogitsLoss, CrossEntropyLoss, MSELoss

import torch.distributed as dist

from transformers.activations import ACT2FN
from transformers.modeling_outputs import BaseModelOutputWithPast, CausalLMOutputWithPast, SequenceClassifierOutputWithPast
from transformers.modeling_utils import PreTrainedModel
from transformers.utils import logging
from transformers.models.llama.configuration_llama import LlamaConfig

from llamao.distributed_attention import DistributedAttention
from flash_attn import flash_attn_kvpacked_func, flash_attn_varlen_kvpacked_func
from flash_attn.bert_padding import unpad_input, pad_input

try:
    from flash_attn.layers.rotary import apply_rotary_emb_func
except ImportError:
    raise ImportError('Please install RoPE kernels: `pip install git+https://github.com/HazyResearch/flash-attention.git#subdirectory=csrc/rotary`')


logger = logging.get_logger(__name__)

# @torch.jit.script
def rmsnorm_func(hidden_states, weight, variance_epsilon):
    input_dtype = hidden_states.dtype
    hidden_states = hidden_states.to(torch.float32)
    variance = hidden_states.pow(2).mean(-1, keepdim=True)
    hidden_states = hidden_states * torch.rsqrt(variance + variance_epsilon)
    return (weight * hidden_states).to(input_dtype)


class LlamaRMSNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-6):
        """
        LlamaRMSNorm is equivalent to T5LayerNorm
        """
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.register_buffer(
            "variance_epsilon",
            torch.tensor(eps),
            persistent=False,
        )

    def forward(self, hidden_states):
        return rmsnorm_func(hidden_states, self.weight, self.variance_epsilon)


class FlashRotaryEmbedding(torch.nn.Module):
    """
    The rotary position embeddings from RoFormer_ (Su et. al).
    A crucial insight from the method is that the query and keys are
    transformed by rotation matrices which depend on the relative positions.

    Other implementations are available in the Rotary Transformer repo_ and in
    GPT-NeoX_, GPT-NeoX was an inspiration

    .. _RoFormer: https://arxiv.org/abs/2104.09864
    .. _repo: https://github.com/ZhuiyiTechnology/roformer
    .. _GPT-NeoX: https://github.com/EleutherAI/gpt-neox

    If scale_base is not None, this implements XPos (Sun et al., https://arxiv.org/abs/2212.10554).
    A recommended value for scale_base is 512: https://github.com/HazyResearch/flash-attention/issues/96
    Reference: https://github.com/sunyt32/torchscale/blob/main/torchscale/component/xpos_relative_position.py
    """

    def __init__(self, dim: int, base=10000.0, interleaved=False, scale_base=None,
                 scaling_factor=1.0, pos_idx_in_fp32=True, device=None):
        """
            interleaved: if True, rotate pairs of even and odd dimensions (GPT-J style) instead
                of 1st half and 2nd half (GPT-NeoX style).
            pos_idx_in_fp32: if True, the position indices [0.0, ..., seqlen - 1] are in fp32,
                otherwise they might be in lower precision.
                This option was added because previously (before 2023-07-02), when we construct
                the position indices, we use the dtype of self.inv_freq. In most cases this would
                be fp32, but if the model is trained in pure bf16 (not mixed precision), then
                self.inv_freq would be bf16, and the position indices are also in bf16.
                Because of the limited precision of bf16 (e.g. 1995.0 is rounded to 2000.0), the
                embeddings for some positions will coincide.
                To maintain compatibility with models previously trained in pure bf16,
                we add this option.
            scaling_factor: RotaryEmbedding extended with linear scaling.
        """
        super().__init__()
        self.dim = dim
        self.base = float(base)
        self.pos_idx_in_fp32 = pos_idx_in_fp32
        # Generate and save the inverse frequency buffer (non trainable)
        inv_freq = self._compute_inv_freq(device)
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.interleaved = interleaved
        self.scale_base = scale_base
        self.scaling_factor = scaling_factor
        scale = ((torch.arange(0, dim, 2, device=device, dtype=torch.float32) + 0.4 * dim)
                 / (1.4 * dim) if scale_base is not None else None)
        self.register_buffer("scale", scale)

        self._seq_len_cached = 0
        self._cos_cached = None
        self._sin_cached = None
        self._cos_k_cached = None
        self._sin_k_cached = None

    def _compute_inv_freq(self, device=None):
        return 1 / (self.base ** (torch.arange(0, self.dim, 2, device=device,
                                                 dtype=torch.float32) / self.dim))


    def _update_cos_sin_cache(self, seqlen, device=None, dtype=None):
        # Reset the tables if the sequence length has changed,
        # if we're on a new device (possibly due to tracing for instance),
        # or if we're switching from inference mode to training
        if (seqlen > self._seq_len_cached or self._cos_cached.device != device
            or self._cos_cached.dtype != dtype
            or (self.training and self._cos_cached.is_inference())):
            self._seq_len_cached = seqlen
            # We want fp32 here, not self.inv_freq.dtype, since the model could be loaded in bf16
            # And the output of arange can be quite large, so bf16 would lose a lot of precision.
            # However, for compatibility reason, we add an option to use the dtype of self.inv_freq.
            if self.pos_idx_in_fp32:
                t = torch.arange(seqlen, device=device, dtype=torch.float32)
                t /= self.scaling_factor
                # We want fp32 here as well since inv_freq will be multiplied with t, and the output
                # will be large. Having it in bf16 will lose a lot of precision and cause the
                # cos & sin output to change significantly.
                # We want to recompute self.inv_freq if it was not loaded in fp32
                if self.inv_freq.dtype != torch.float32:
                    inv_freq = self.inv_freq.to(torch.float32)
                else:
                    inv_freq = self.inv_freq
            else:
                t = torch.arange(seqlen, device=device, dtype=self.inv_freq.dtype)
                t /= self.scaling_factor
                inv_freq = self.inv_freq
            # Don't do einsum, it converts fp32 to fp16 under AMP
            # freqs = torch.einsum("i,j->ij", t, self.inv_freq)
            freqs = torch.outer(t, inv_freq)
            if self.scale is None:
                self._cos_cached = torch.cos(freqs).to(dtype)
                self._sin_cached = torch.sin(freqs).to(dtype)
            else:
                power = ((torch.arange(seqlen, dtype=self.scale.dtype, device=self.scale.device)
                          - seqlen // 2) / self.scale_base)
                scale = self.scale.to(device=power.device) ** power.unsqueeze(-1)
                # We want the multiplication by scale to happen in fp32
                self._cos_cached = (torch.cos(freqs) * scale).to(dtype)
                self._sin_cached = (torch.sin(freqs) * scale).to(dtype)
                self._cos_k_cached = (torch.cos(freqs) / scale).to(dtype)
                self._sin_k_cached = (torch.sin(freqs) / scale).to(dtype)

    def forward(self,
                q: torch.Tensor, k: torch.Tensor,
                seqlen_offset: int = 0,
                unpadded_lengths: Optional[tuple[torch.Tensor]] = None) -> tuple[torch.Tensor, torch.Tensor]:
        """
        q: (batch, seqlen, nheads, headdim)
        k: (batch, seqlen, nheads, headdim)
        seqlen_offset: can be used in generation where the qkv being passed in is only the last
        token in the batch.
        """
        if unpadded_lengths is not None:
            cu_seqlens, max_seqlen = unpadded_lengths
        else:
            cu_seqlens, max_seqlen = None, q.shape[1]
        self._update_cos_sin_cache(max_seqlen + seqlen_offset, device=q.device, dtype=q.dtype)

        if self.scale is None:
            return apply_rotary_emb_func(
                q, self._cos_cached[seqlen_offset:], self._sin_cached[seqlen_offset:],
                self.interleaved, True, # inplace=True,
                cu_seqlens=cu_seqlens, max_seqlen=max_seqlen
            ), apply_rotary_emb_func(
                k, self._cos_cached[seqlen_offset:], self._sin_cached[seqlen_offset:],
                self.interleaved, True, # inplace=True
                cu_seqlens=cu_seqlens, max_seqlen=max_seqlen
            )
        else:
            assert False


class LlamaMLP(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.intermediate_size = config.intermediate_size
        self.gate_proj = nn.Linear(self.hidden_size, self.intermediate_size, bias=False)
        self.up_proj = nn.Linear(self.hidden_size, self.intermediate_size, bias=False)
        self.down_proj = nn.Linear(self.intermediate_size, self.hidden_size, bias=False)
        self.act_fn = ACT2FN[config.hidden_act]

    def forward(self, x):
        return self.down_proj(self.act_fn(self.gate_proj(x)) * self.up_proj(x))


@torch.jit.script
def repeat_kv(hidden_states: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    This is the equivalent of torch.repeat_interleave(x, dim=1, repeats=n_rep). The hidden states go from (batch,
    num_key_value_heads, seqlen, head_dim) to (batch, num_attention_heads, seqlen, head_dim)
    """
    if n_rep == 1:
        return hidden_states
    final_shape = list(hidden_states.shape[:-2]) + [-1] + [hidden_states.shape[-1]]
    expand_shape = [-1] * (len(hidden_states.shape) - 1) + [n_rep] + [-1]
    hidden_states = hidden_states.unsqueeze(-1).expand(expand_shape)
    return hidden_states.reshape(final_shape)


class LlamaAttention(nn.Module):
    """Multi-headed attention from 'Attention Is All You Need' paper"""

    def __init__(self, config: LlamaConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.head_dim = self.hidden_size // self.num_heads
        self.num_key_value_heads = getattr(config, "num_key_value_heads", self.num_heads)
        self.num_key_value_groups = self.num_heads // self.num_key_value_heads
        self.max_position_embeddings = config.max_position_embeddings

        if (self.head_dim * self.num_heads) != self.hidden_size:
            raise ValueError(
                f"hidden_size must be divisible by num_heads (got `hidden_size`: {self.hidden_size}"
                f" and `num_heads`: {self.num_heads})."
            )
        self.q_proj = nn.Linear(self.hidden_size, self.num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(self.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(self.num_heads * self.head_dim, self.hidden_size, bias=False)

        self.register_buffer(
            "norm_factor",
            torch.sqrt(torch.tensor(self.head_dim, dtype=torch.float32)).to(torch.get_default_dtype()),
            persistent=False,
        )

        if not getattr(self.config, "rope_scaling", None):
            scaling_factor = 1
        else:
            scaling_type = self.config.rope_scaling["type"]
            scaling_factor = self.config.rope_scaling["factor"]
            assert scaling_type == 'linear'
        theta = getattr(self.config, "rope_theta", 10000)
        self.rotary_emb = FlashRotaryEmbedding(
            self.head_dim, base=theta, interleaved=False, scaling_factor=scaling_factor,
        )

        self.distributed_attn_func = DistributedAttention(flash_attn_kvpacked_func)

    def _shape(self, tensor: torch.Tensor, seq_len: int, bsz: int):
        return tensor.view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2).contiguous()

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[tuple[torch.Tensor]] = None,
        output_attentions: bool = False,
        use_cache: bool = False,
        unpadded_lengths: Optional[tuple[torch.Tensor]] = None,
        seq_parallel_group: Optional[Any] = None,
    ) -> tuple[torch.Tensor, Optional[torch.Tensor], Optional[tuple[torch.Tensor]]]:
        h_size = hidden_states.size(-1)

        has_layer_past = past_key_value is not None

        if has_layer_past:
            past_kv = past_key_value[0]
            past_len = past_key_value[1]
        else:
            past_len = 0

        # NOTE: Hack to include position_ids, assuming they are increasing uniformly per block
        if position_ids is not None:
            past_len += position_ids.min()

        q = self.q_proj(hidden_states)
        k = self.k_proj(hidden_states)
        v = self.v_proj(hidden_states)

        q = q.view(*q.shape[:-1], self.num_heads, self.head_dim)
        k = k.view(*k.shape[:-1], self.num_key_value_heads, self.head_dim)
        v = v.view(*v.shape[:-1], self.num_key_value_heads, self.head_dim)

        q, k = self.rotary_emb(q, k, past_len, unpadded_lengths)

        kv = torch.stack([k, v], -3)
        kv = repeat_kv(kv, self.num_key_value_groups)

        # Cache QKV values
        if has_layer_past:
            new_len = past_len+q.size(1)
            if new_len > past_kv.size(1):
                past_kv = torch.cat([past_kv, torch.empty(hidden_states.size(0), 256, 2, kv.size(3), kv.size(4), dtype=kv.dtype, device=kv.device)], 1)
            past_kv[:, past_len:new_len] = kv
            kv = past_kv[:, :new_len]
        else:
            past_kv = kv

        past_key_value = (past_kv, past_len+q.size(1)) if use_cache else None

        if dist.is_initialized() and dist.get_world_size(seq_parallel_group) > 1:
            # NOTE: we assume that padding tokens are at the end of the sequence and may ignore `attention_mask`
            assert output_attentions is False
            attn_outputs = self.distributed_attn_func(
                q, kv,
                dropout_p=0.0,
                softmax_scale=1.0/self.norm_factor,
                causal=True,
                return_attn_probs=False,
                group=seq_parallel_group
            )
        else:
            if unpadded_lengths is not None:
                # varlen, ignore padding tokens, efficient for large batch with many paddings
                assert attention_mask is not None
                cu_seqlens, max_seqlen = unpadded_lengths

                attn_outputs = flash_attn_varlen_kvpacked_func(
                    q, kv,
                    cu_seqlens, cu_seqlens,
                    max_seqlen, max_seqlen,
                    dropout_p=0.0, softmax_scale=1.0/self.norm_factor,
                    causal=True, return_attn_probs=output_attentions
                )
            else:
                attn_outputs = flash_attn_kvpacked_func(
                    q, kv,
                    dropout_p=0.0,
                    softmax_scale=1.0/self.norm_factor,
                    causal=True,
                    return_attn_probs=output_attentions,
                )

        attn_output = attn_outputs[0] if output_attentions else attn_outputs
        attn_output = attn_output.reshape(*attn_output.shape[:-2], h_size)
        attn_weights = attn_outputs[2] if output_attentions else None

        attn_output = self.o_proj(attn_output)

        if not output_attentions:
            attn_weights = None

        return attn_output, attn_weights, past_key_value


class LlamaDecoderLayer(nn.Module):
    def __init__(self, config: LlamaConfig):
        super().__init__()
        self.hidden_size = config.hidden_size
        self.self_attn = LlamaAttention(config=config)
        self.mlp = LlamaMLP(config)
        self.input_layernorm = LlamaRMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.post_attention_layernorm = LlamaRMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self._fsdp_wrap = True

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[tuple[torch.Tensor]] = None,
        unpadded_lengths: Optional[tuple[torch.Tensor]] = None,
        output_attentions: Optional[bool] = False,
        use_cache: Optional[bool] = False,
        seq_parallel_group: Optional[Any] = None,
    ) -> tuple[torch.FloatTensor, Optional[tuple[torch.FloatTensor, torch.FloatTensor]]]:
        """
        Args:
            hidden_states (`torch.FloatTensor`): input to the layer of shape `(batch, seq_len, embed_dim)`
            attention_mask (`torch.FloatTensor`, *optional*): attention mask of size
                `(batch, 1, tgt_len, src_len)` where padding elements are indicated by very large negative values.
            output_attentions (`bool`, *optional*):
                Whether or not to return the attentions tensors of all attention layers. See `attentions` under
                returned tensors for more detail.
            use_cache (`bool`, *optional*):
                If set to `True`, `past_key_values` key value states are returned and can be used to speed up decoding
                (see `past_key_values`).
            past_key_value (`Tuple(torch.FloatTensor)`, *optional*): cached past key and value projection states
        """

        residual = hidden_states

        hidden_states = self.input_layernorm(hidden_states)

        # Self Attention
        hidden_states, self_attn_weights, present_key_value = self.self_attn(
            hidden_states=hidden_states,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_value=past_key_value,
            output_attentions=output_attentions,
            use_cache=use_cache,
            unpadded_lengths=unpadded_lengths,
            seq_parallel_group=seq_parallel_group,
        )
        hidden_states = residual + hidden_states

        # Fully Connected
        residual = hidden_states
        hidden_states = self.post_attention_layernorm(hidden_states)
        hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states

        outputs = (hidden_states,)

        if output_attentions:
            outputs += (self_attn_weights,)

        if use_cache:
            outputs += (present_key_value,)

        return outputs


class LlamaPreTrainedModel(PreTrainedModel):
    config_class = LlamaConfig
    base_model_prefix = "model"
    supports_gradient_checkpointing = True
    _no_split_modules = ["LlamaDecoderLayer"]
    _skip_keys_device_placement = "past_key_values"

    def _init_weights(self, module):
        std = self.config.initializer_range
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=std)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=std)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()

    def _set_gradient_checkpointing(self, module, value=False):
        if isinstance(module, LlamaModel):
            module.gradient_checkpointing = value


class LlamaModel(LlamaPreTrainedModel):
    """
    Transformer decoder consisting of *config.num_hidden_layers* layers. Each layer is a [`LlamaDecoderLayer`]

    Args:
        config: LlamaConfig
    """

    def __init__(self, config: LlamaConfig):
        super().__init__(config)
        self.padding_idx = config.pad_token_id
        self.vocab_size = config.vocab_size

        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size, self.padding_idx)
        self.layers = nn.ModuleList([LlamaDecoderLayer(config) for _ in range(config.num_hidden_layers)])
        self.norm = LlamaRMSNorm(config.hidden_size, eps=config.rms_norm_eps)

        self.gradient_checkpointing = False
        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.embed_tokens

    def set_input_embeddings(self, value):
        self.embed_tokens = value

    def forward(
        self,
        input_ids: torch.LongTensor = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[list[torch.FloatTensor]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        seq_parallel_group: Optional[Any] = None,
    ) -> Union[tuple, BaseModelOutputWithPast]:
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        use_cache = use_cache if use_cache is not None else self.config.use_cache

        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        # retrieve input_ids and inputs_embeds
        if input_ids is not None and inputs_embeds is not None:
            raise ValueError("You cannot specify both decoder_input_ids and decoder_inputs_embeds at the same time")
        elif input_ids is not None:
            batch_size, seq_length = input_ids.shape
        elif inputs_embeds is not None:
            batch_size, seq_length, _ = inputs_embeds.shape
        else:
            raise ValueError("You have to specify either decoder_input_ids or decoder_inputs_embeds")

        # position_ids = None

        if inputs_embeds is None:
            inputs_embeds = self.embed_tokens(input_ids)

        hidden_states = inputs_embeds
        bsz = hidden_states.size(0)

        if self.gradient_checkpointing and self.training:
            if use_cache:
                logger.warning_once(
                    "`use_cache=True` is incompatible with gradient checkpointing. Setting `use_cache=False`..."
                )
                use_cache = False

        if (
            ((attention_mask is not None) and (not attention_mask.all().item()))
            and not use_cache
            and not (dist.is_initialized() and dist.get_world_size(seq_parallel_group) > 1)
        ):
            hidden_states, unpad_indices, cu_seqlens, max_seqlen = unpad_input(hidden_states, attention_mask)
            unpadded_lengths = (cu_seqlens, max_seqlen)
        else:
            unpadded_lengths = None

        # decoder layers
        all_hidden_states = () if output_hidden_states else None
        all_self_attns = () if output_attentions else None
        next_decoder_cache = () if use_cache else None

        for idx, decoder_layer in enumerate(self.layers):
            if output_hidden_states:
                if unpadded_lengths is not None:
                    all_hidden_states += (pad_input(hidden_states, unpad_indices, bsz, max_seqlen),)
                else:
                    all_hidden_states += (hidden_states,)

            past_key_value = past_key_values[idx] if past_key_values is not None else None

            if self.gradient_checkpointing and self.training:
                layer_outputs = torch.utils.checkpoint.checkpoint(
                    decoder_layer,
                    hidden_states,
                    attention_mask,
                    position_ids,
                    None,
                    unpadded_lengths,
                    output_attentions,
                    False,
                    seq_parallel_group
                )
            else:
                layer_outputs = decoder_layer(
                    hidden_states,
                    attention_mask=attention_mask,
                    position_ids=position_ids,
                    past_key_value=past_key_value,
                    unpadded_lengths=unpadded_lengths,
                    output_attentions=output_attentions,
                    use_cache=use_cache,
                    seq_parallel_group=seq_parallel_group,
                )

            hidden_states = layer_outputs[0]

            if use_cache:
                next_decoder_cache += (layer_outputs[2 if output_attentions else 1],)

            if output_attentions:
                all_self_attns += (layer_outputs[1],)

        if unpadded_lengths is not None:
            hidden_states = pad_input(hidden_states, unpad_indices, bsz, max_seqlen)
        hidden_states = self.norm(hidden_states)

        # add hidden states from the last decoder layer
        if output_hidden_states:
            all_hidden_states += (hidden_states,)

        next_cache = next_decoder_cache if use_cache else None
        if not return_dict:
            return tuple(v for v in [hidden_states, next_cache, all_hidden_states, all_self_attns] if v is not None)
        return BaseModelOutputWithPast(
            last_hidden_state=hidden_states,
            past_key_values=next_cache,
            hidden_states=all_hidden_states,
            attentions=all_self_attns,
        )


class LlamaForCausalLM(LlamaPreTrainedModel):
    _tied_weights_keys = ["lm_head.weight"]

    def __init__(self, config):
        super().__init__(config)
        self.model = LlamaModel(config)
        self.vocab_size = config.vocab_size
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        self.model.embed_tokens = value

    def get_output_embeddings(self):
        return self.lm_head

    def set_output_embeddings(self, new_embeddings):
        self.lm_head = new_embeddings

    def set_decoder(self, decoder):
        self.model = decoder

    def get_decoder(self):
        return self.model

    def forward(
        self,
        input_ids: torch.LongTensor = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[list[torch.FloatTensor]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        unpadded_lengths: Optional[bool] = None,
        avg_valid_labels_per_chunk: Optional[float] = None,
        seq_parallel_group: Optional[Any] = None,
    ) -> Union[tuple, CausalLMOutputWithPast]:
        r"""
        Args:
            labels (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
                Labels for computing the masked language modeling loss. Indices should either be in `[0, ...,
                config.vocab_size]` or -100 (see `input_ids` docstring). Tokens with indices set to `-100` are ignored
                (masked), the loss is only computed for the tokens with labels in `[0, ..., config.vocab_size]`.

        Returns:

        Example:

        ```python
        >>> from transformers import AutoTokenizer, LlamaForCausalLM

        >>> model = LlamaForCausalLM.from_pretrained(PATH_TO_CONVERTED_WEIGHTS)
        >>> tokenizer = AutoTokenizer.from_pretrained(PATH_TO_CONVERTED_TOKENIZER)

        >>> prompt = "Hey, are you conscious? Can you talk to me?"
        >>> inputs = tokenizer(prompt, return_tensors="pt")

        >>> # Generate
        >>> generate_ids = model.generate(inputs.input_ids, max_length=30)
        >>> tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        "Hey, are you conscious? Can you talk to me?\nI'm not conscious, but I can talk to you."
        ```"""

        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        # decoder outputs consists of (dec_features, layer_state, dec_hidden, dec_attn)
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
            seq_parallel_group=seq_parallel_group,
        )

        hidden_states = outputs[0]
        loss = None
        if labels is not None:
            # Only compute loss on tokens that contribute to loss
            valid_prediction = (labels != -100)
            hidden_states_ = hidden_states[valid_prediction]
            logits = self.lm_head(hidden_states_).float()

            # NOTE: We don't shift the labels inside the model here!
            labels_ = labels[valid_prediction]

            if avg_valid_labels_per_chunk is not None and avg_valid_labels_per_chunk > 0:
                # Don't take mean since this will give unequal weight to GPUs with unequal amount of padding
                loss = F.cross_entropy(logits, labels_, reduction="mean") * (labels_.numel() / avg_valid_labels_per_chunk)
                if not valid_prediction.any():
                    loss.data = torch.zeros_like(loss)
            else:
                loss = F.cross_entropy(logits, labels_, reduction="mean")
        else:
            logits = self.lm_head(hidden_states).float()

        if not return_dict:
            output = (logits,) + outputs[1:]
            return (loss,) + output if loss is not None else output

        return CausalLMOutputWithPast(
            loss=loss,
            logits=logits,
            past_key_values=outputs.past_key_values,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

    def prepare_inputs_for_generation(
        self, input_ids, past_key_values=None, attention_mask=None, inputs_embeds=None, **kwargs
    ):
        if past_key_values:
            input_ids = input_ids[:, -1:]

        # if `inputs_embeds` are passed, we only want to use them in the 1st generation step
        if inputs_embeds is not None and past_key_values is None:
            model_inputs = {"inputs_embeds": inputs_embeds}
        else:
            model_inputs = {"input_ids": input_ids}

        model_inputs.update(
            {
                "position_ids": kwargs.get("position_ids", None),
                "past_key_values": past_key_values,
                "use_cache": kwargs.get("use_cache"),
                "attention_mask": attention_mask,
                "unpadded_lengths": ((attention_mask is not None) and (not attention_mask.all().item())),
                "seq_parallel_group": kwargs.get("seq_parallel_group"),
            }
        )
        return model_inputs

    @staticmethod
    def _reorder_cache(past_key_values, beam_idx):
        reordered_past = ()
        for layer_past in past_key_values:
            reordered_past += (
                tuple(past_state.index_select(0, beam_idx.to(past_state.device)) for past_state in layer_past),
            )
        return reordered_past


class LlamaForSequenceClassification(LlamaPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.model = LlamaModel(config)
        self.score = nn.Linear(config.hidden_size, self.num_labels, bias=False)

        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        self.model.embed_tokens = value

    def forward(
        self,
        input_ids: torch.LongTensor = None,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_values: Optional[list[torch.FloatTensor]] = None,
        inputs_embeds: Optional[torch.FloatTensor] = None,
        labels: Optional[torch.LongTensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[tuple, SequenceClassifierOutputWithPast]:
        r"""
        labels (`torch.LongTensor` of shape `(batch_size,)`, *optional*):
            Labels for computing the sequence classification/regression loss. Indices should be in `[0, ...,
            config.num_labels - 1]`. If `config.num_labels == 1` a regression loss is computed (Mean-Square loss), If
            `config.num_labels > 1` a classification loss is computed (Cross-Entropy).
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        transformer_outputs = self.model(
            input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = transformer_outputs[0]
        logits = self.score(hidden_states)

        if input_ids is not None:
            batch_size = input_ids.shape[0]
        else:
            batch_size = inputs_embeds.shape[0]

        if self.config.pad_token_id is None and batch_size != 1:
            raise ValueError("Cannot handle batch sizes > 1 if no padding token is defined.")
        if self.config.pad_token_id is None:
            sequence_lengths = -1
        else:
            if input_ids is not None:
                sequence_lengths = (torch.ne(input_ids, self.config.pad_token_id).sum(-1) - 1).to(logits.device)
            else:
                sequence_lengths = -1

        pooled_logits = logits[torch.arange(batch_size, device=logits.device), sequence_lengths]

        loss = None
        if labels is not None:
            labels = labels.to(logits.device)
            if self.config.problem_type is None:
                if self.num_labels == 1:
                    self.config.problem_type = "regression"
                elif self.num_labels > 1 and (labels.dtype == torch.long or labels.dtype == torch.int):
                    self.config.problem_type = "single_label_classification"
                else:
                    self.config.problem_type = "multi_label_classification"

            if self.config.problem_type == "regression":
                loss_fct = MSELoss()
                if self.num_labels == 1:
                    loss = loss_fct(pooled_logits.squeeze(), labels.squeeze())
                else:
                    loss = loss_fct(pooled_logits, labels)
            elif self.config.problem_type == "single_label_classification":
                loss_fct = CrossEntropyLoss()
                loss = loss_fct(pooled_logits.view(-1, self.num_labels), labels.view(-1))
            elif self.config.problem_type == "multi_label_classification":
                loss_fct = BCEWithLogitsLoss()
                loss = loss_fct(pooled_logits, labels)
        if not return_dict:
            output = (pooled_logits,) + transformer_outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return SequenceClassifierOutputWithPast(
            loss=loss,
            logits=pooled_logits,
            past_key_values=transformer_outputs.past_key_values,
            hidden_states=transformer_outputs.hidden_states,
            attentions=transformer_outputs.attentions,
        )
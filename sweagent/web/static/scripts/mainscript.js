function addMessageToFeed(feedID, title, text, format, step) {
    console.log("in addMessageToFeed");

    let classes = "message"
    if (step !== null) {
        classes += " step" + step;
        title += " (step " + step + ")";

    }
    const $feed = $(feedID);
    const $messageBlock = $('<div>', { class: classes});

    if (title) {
        $('<h4>', { text: title}).appendTo($messageBlock);
    }

    let $messageText;
    if (format === "text") {
        $messageText = $('<p>', { text: text });
    } else if (format === "markdown") {
        $messageText = $('<md-block>', { text: text }); // Note: Custom elements need to be handled properly in jQuery
    } else {
        console.error("Unknown format: " + format);
        return;
    }

    $messageBlock.append($messageText).appendTo($feed);
    $feed.scrollTop($feed.prop("scrollHeight")); // jQuery method to scroll to the bottom
}

function highlightStep(step) {
    // Highlight all actions, thoughts, etc. of one specific step
    $('.message').removeClass('highlight');
    $(`.message.step${step}`).addClass('highlight');
}

function removeAllMessagesFromFeed(feedID) {
    const $feed = $(feedID);
    $feed.find('.message').remove();
}


document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    socket.on('update', function(data) {
        feed = '#' + data["feed"] + "Feed";
        addMessageToFeed(feed, data["title"], data["message"], data["format"], data["thought_idx"]);
    });
});


function findFirstMessageForStep(feedName, step) {
    // Find the first element with class 'message' and 'stepX' within the specified feed
    const selector = `#${feedName} .message.step${step}`;
    return $(selector).first(); 
}


function scrollToFirstMessageForStep(feedName, step) {
    const $message = findFirstMessageForStep(feedName, step);
    const $container = $(`#${feedName}`);
    const scrollTo = $message.offset().top - $container.offset().top + $container.scrollTop();
    $container.animate({ scrollTop: scrollTo }, 'slow'); 
}
import MacBar from '../MacBar';
import editorLogo from '../../assets/panel_icons/editor.png';
import "../../static/logPanel.css";
import { Button } from 'react-bootstrap';
import { Clipboard } from 'react-bootstrap-icons';

const LogPanel = ({ logs, logsRef, setIsTerminalExpanded}) => {

  const copyToClipboard = (text) => {
    // Create a temporary textarea element
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);

    // Select and copy the text
    textarea.select();
    document.execCommand('copy');

    // Clean up
    document.body.removeChild(textarea);
  };

  const handleCopy = () => {
    const contentToCopy = document.getElementById('logContent').innerText;
    copyToClipboard(contentToCopy);
  };

    return (
        <div id="logPanel" className="logPanel">
            <MacBar
              logo={editorLogo}
              title="Log file"
              dark={true}
            />
            <div className="scrollableDiv"  ref={logsRef}>
              <div className="innerDiv">
                <pre id="logContent">{logs}</pre>
                <div style={{ clear: "both", marginTop: '1em' }}/>
              </div>
              <div style={{ display: 'flex', justifyContent: 'right', width: '100%' }}>
                <Button variant="light" onClick={handleCopy} style={{marginBottom: 20, marginRight: 20}}>
                  <Clipboard /> Copy to clipboard
                </Button>
              </div>
            </div>
        </div>
    );
};

export default LogPanel;

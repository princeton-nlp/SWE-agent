function addMessageToFeed(feedID, title, text, format) {
    console.log("in addMessageToFeed");
    const feed = document.getElementById(feedID);
    const messageBlock = document.createElement('div');
    messageBlock.className = 'message';

    if ( title != null && title.length > 0 ) {
        const messageTitle = document.createElement('h4');
        messageTitle.textContent = title;
        messageBlock.appendChild(messageTitle);
    }

    let messageText;
    if ( format == "text" ) {
        messageText = document.createElement('p');
        messageText.textContent = text;
    }
    else if ( format == "markdown" ) {
        messageText = document.createElement('md-block');
        messageText.textContent = text;
    }
    else {
        console.error("Unknown format: " + format);
    }

    messageBlock.appendChild(messageText);

    feed.appendChild(messageBlock);
    feed.scrollTop = feed.scrollHeight;
}


document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    socket.on('update', function(data) {
        feed = data["feed"] + "Feed";
        addMessageToFeed(feed, data["title"], data["message"], data["format"]);
    });
});
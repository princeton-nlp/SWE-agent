function addMessageToFeed(feedID, title, text) {
    console.log("in addMessageToFeed");
    const feed = document.getElementById(feedID);
    const messageBlock = document.createElement('div');
    messageBlock.className = 'message';

    const messageTitle = document.createElement('h4');
    messageTitle.textContent = title;

    const messageText = document.createElement('p');
    messageText.textContent = text;

    messageBlock.appendChild(messageTitle);
    messageBlock.appendChild(messageText);

    feed.appendChild(messageBlock);
}


document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    socket.on('update', function(data) {
        console.log("update");
        addMessageToFeed('agentFeed', data["event"], JSON.stringify(data));
        addMessageToFeed('envFeed', data["event"], JSON.stringify(data));
    });
});
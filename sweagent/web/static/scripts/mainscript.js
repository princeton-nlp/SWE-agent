function addMessageToFeed(feedID, title, text, format) {
    console.log("in addMessageToFeed");

    const $feed = $(feedID);
    const $messageBlock = $('<div>', { class: 'message' });

    if (title) {
        $('<h4>', { text: title }).appendTo($messageBlock);
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


document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    socket.on('update', function(data) {
        feed = '#' + data["feed"] + "Feed";
        addMessageToFeed(feed, data["title"], data["message"], data["format"]);
    });
});
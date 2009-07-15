document.observe('dom:loaded', function() {
    $A(document.getElementsByClassName('quote-header')).each(function(item) {
        $(item).observe('click', loadquote)
    })
});

function loadquote() {
    element = $(this).next()
    if(element.innerHTML == '') {
        id = element.id.split('-')[1];
        new Ajax.Updater(element, '/quotes/' + id, {
            method: 'get',
            onSuccess: function() {
                element.show()
            }
        });
    } else if(element.visible()) {
        element.hide()
    } else {
        element.show()
    }
}
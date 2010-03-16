// support for toggleable sections
$(document).ready(function() {
  $('div.toggleable').each(function() {
    var
    fieldset = $(this),
    children = fieldset.children().slice(1);
    // collapse it if it should be collapsed and there are no errors in there
    if ($(this).is('.collapsed') && $('.errors', this).length == 0)
      children.hide();
    $('h3', this).click(function() {
      children.toggle();
      fieldset.toggleClass('collapsed');
    });
  });
});

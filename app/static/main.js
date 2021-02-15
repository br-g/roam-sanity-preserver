var query = ''
var n_results = 0
var search_in_progress = false
var search_completed = false


function search() {
    if (query.length == 0 || search_in_progress || search_completed)
        return

    search_in_progress = true
    // $('#loading_spinner').css('display', 'block')

    $.getJSON($SCRIPT_ROOT + '/search', {
        query: query,
        offset: n_results
    }, function(data) {
        n_results += data['n_results']
        $('#search_results').append(data['html']);
        if (data['n_results'] == 0)
            search_completed = true
        // $('#loading_spinner').hide()
    }).always(function() {
      search_in_progress = false
    });

}


$(document).ready(function() {
    const textField = new mdc.textField.MDCTextField(document.querySelector('.mdc-text-field'));
    textField.focus();

    $('#search_bar').on('keyup', function (e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            n_results = 0
            search_completed = false
          $('#search_results').empty();
          query = $('#search_bar input').val()
          search()
        }
    });

    $('#search_button').click(function() {
      n_results = 0
      search_completed = false
      $('#search_results').empty();
      query = $('#search_bar input').val()
      search()
    });

    // inifinite scrolling
    $(window).on('scroll', function(){
        if (n_results == 0)
            return
        var scroll_top = $(document).scrollTop();
        var window_height = $(window).height();
        var body_height = $(document).height() - window_height;
        var scroll_percentage = (scroll_top / body_height);
        if(scroll_percentage > 0.9) {
          search()
        }
    });

    // show more / show less
    $(document).on('click', '.search_result .show_more', function() {
        $(this).hide()
        $(this).parent().find('.content.short').hide()
        $(this).parent().find('.content.long').show()
        $(this).parent().find('.show_less').css({'display': 'block'})
    })
    $(document).on('click', '.search_result .show_less', function() {
        $(this).hide()
        $(this).parent().find('.content.long').hide()
        $(this).parent().find('.content.short').show()
        $(this).parent().find('.show_more').css({'display': 'block'})
    })
});

 /* @license  AGPL-3.0-or-later*/
'use strict';
// g for global, which will be a reserved variable during mangling
window.g = {};
window.g.__SESSION_QUESTION_PKS = Object.keys(window.SESSION_QUESTIONS).map(function(x){ return parseInt(x)});
window.g.__SESSION_QUESTION_GLOBAL_SEQUENCES = window.g.__SESSION_QUESTION_PKS.map(function(x){ return window.SESSION_QUESTIONS[x] }).sort(function(a, b){ return a - b});
window.g.__SESSION_QUESTION_TOTAL = window.g.__SESSION_QUESTION_PKS.length;
window.g.__PREVIOUS_HIGHLIGHTS = null;
window.g.__MARKS = null;
window.g.__ANSWERS = null;
window.g.__STATS = null;
window.g.__HAS_CONSTRUCTED_NAVIGATION = false;
window.g.__SHARED_STAT_TIMER = null;
window.g.__IS_PRESENTER = window.location.search.search(/[\?&]presenter=/) != -1;

// Sort SESSION_QUESTION_PKS per their global_sequences, if those
// do not include any null values.  Otherwise, sort per pks.
if (window.g.__SESSION_QUESTION_GLOBAL_SEQUENCES.indexOf(null) != -1){
  window.g.__SESSION_QUESTION_PKS = window.g.__SESSION_QUESTION_PKS.sort(function(a, b){return window.SESSION_QUESTIONS[a] - window.SESSION_QUESTIONS[b]});
} else {
  window.g.__SESSION_QUESTION_PKS = window.g.__SESSION_QUESTION_PKS.sort(function(a, b){return a - b});
}

var converter = new showdown.Converter({headerLevelStart: 3, simpleLineBreaks: true, noHeaderId: true});


// Common selectors
window.g.__$markButton = $("#mark");
window.g.__$submitButton = $("#submit");

window.g.__fetched_indexes = [],
window.g.__active_keys = {},
window.g.__animation_events = 'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
window.g.__was_solved_markup = '<i class="far fa-check-square"></i>',
window.g.__is_marked_markup = '<i class="fas fa-flag"></i>',
window.g.__wrong_answer_markup = '<i class="fas fa-times text-danger mx-1"></i>',
window.g.__isTablet = navigator.userAgent.match(/iPad/i) != null || (navigator.userAgent.match(/Android/i) != null && navigator.userAgent.match(/Mobile/i) == null),
window.g.__isMobile = navigator.userAgent.match(/iPhone/i) != null || (navigator.userAgent.match(/Android/i) != null && navigator.userAgent.match(/Mobile/i) != null);

toastr.options.positionClass = "toast-top-left";
toastr.options.preventDuplicates = true;

function handleMarked(is_marked){
    if (is_marked){
        window.g.__$markButton.addClass("marked");
    } else {
        window.g.__$markButton.removeClass("marked");
    }
}

function showQuestion(target, is_initial){
  // 'target' could either be a question-sequence or url.  First,
  // let's check sequence, then URL.
  window.g.__$current_question = $("#question-pool [data-question-sequence=\"" + target + "\"]")
  if (window.g.__$current_question.length){
    if (is_initial){
      history.replaceState({url: window.g.__$current_question.data('url')}, '', window.g.__$current_question.data('url'));
    } else {
      history.pushState({url: window.g.__$current_question.data('url')}, '', window.g.__$current_question.data('url'));
    }
    // Update Piwik URL
    _paq.push(['setCustomUrl', window.location.href]);
  } else {
    window.g.__$current_question = $("#question-pool [data-url=\"" + target + "\"]");
  }

  window.g.__$current_question.find('.lazy').each(function(){
    var $lazy_loader = $(this),
        src = $lazy_loader.data('src'),
        img_class = $lazy_loader.data('img-class'),
        $lazy_img = $('<img class="d-none ' + img_class + '" src="' + src + '">');
    $lazy_img.on('load', function(){
      var gallary_name = $(this).closest('[data-fancybox]').data('fancybox');
      $lazy_loader.remove();
      $(this).removeClass('d-none');
      $('[data-fancybox="' + gallary_name + '"]').fancybox({
      buttons: [
          "zoom",
          "download",
          "close"
        ],
      beforeShow: function(){
        $(document).off('keydown keydup');
      },
      afterClose: function(){
        initializeKeyboard();
      }});

    });
    $lazy_loader.after($lazy_img);
  });

  // If question is still unfound despite looking by URL,
  // fetch it.
  if (!window.g.__$current_question.length) {
    var question_set_start_index = Math.floor(target / 50) * 50;
    fetchList(question_set_start_index, target);
    return
  }

  // Add 'show' class to the current question
  window.g.__$current_question.addClass("show");
  // Remove 'show' class from other questions
  $(".question-body").not(window.g.__$current_question).removeClass('show');
  // The following is intentionally a global variable.
  window.g.__current_sequence = window.g.__$current_question.data('question-sequence');
  $("#question-sequence").html(window.g.__current_sequence);
  var list_revision_url = window.g.__$current_question.data('list-revision-url')
  $("#question-pk").html(window.g.__$current_question.data('question-pk'))
                   .attr('href', list_revision_url);

  initializeInteractions();

  // We will fetch questions in two cases:
  //   1) If this is the initial question, fetch its question set.
  //   2) If this is the initial question and 10 questions away or less from previous or next question set, fetch either.
  //   3) If this is not the initial question, and we are 10 questions away from it, fetch the next question set.

  var current_set_start_index = Math.floor(window.g.__current_sequence / 50) * 50,
      next_set_start_index = (Math.floor(window.g.__current_sequence / 50) + 1) * 50,
      previous_set_start_index = (Math.floor(window.g.__current_sequence / 50) - 1) * 50,
      previous_set_end_index = current_set_start_index - 1;

  if (next_set_start_index >= window.g.__SESSION_QUESTION_TOTAL){
    next_set_start_index = null;
  }
  if (0 > previous_set_start_index){
    previous_set_start_index = null;
  }

  if (is_initial){
    fetchList(current_set_start_index)
  }

  if (
    (is_initial &&
     next_set_start_index &&
     window.g.__current_sequence >= (next_set_start_index - 10)) ||
     (!is_initial &&
      next_set_start_index &&
      window.g.__current_sequence == (next_set_start_index - 10))
    ){
      fetchList(next_set_start_index)
  }

  if (
    (is_initial &&
     previous_set_start_index !== null &&
     window.g.__current_sequence <= (previous_set_end_index + 10)) ||
     (!is_initial &&
      previous_set_start_index !== null &&
      window.g.__current_sequence == (previous_set_end_index + 10))
    ){
      fetchList(previous_set_start_index)
  }

  if (window.g.__IS_PRESENTER){
    var question_id = window.g.__$current_question.data('question-id'),
        chart_context = window.g.__$current_question.find('.presenter-stats').get(0).getContext('2d'),
        choice_ids = [],
        data = {datasets: [{data: []}], labels: []};

    // The goal here is to get a sorted list of choices bassed on the id
    window.g.__$current_question.find('tr[data-choice-pk]').each(function(){
      var choice_id = $(this).data('choice-pk');
      choice_ids.push(choice_id)
    });
    choice_ids.sort()
    for (var i = 0; i < choice_ids.length; i++) {
      var choice_id = choice_ids[i],
          choice_text = $('#choice-text-' + choice_id).text();
      data.labels.push(choice_text);
    }
    window.g.__$current_question.find('.presneter-stat-container').show();
    var chart = new Chart(chart_context, {type: 'pie', data: data});
    window.g.__chart = chart;
    fetchSharedStats();
  }
}

window.onpopstate = function(event) {
  if (event.state){
    showQuestion(event.state.url)
  }
};

function navigate() {
    var action = $(this).data('action');

    // If no previous or no next, just return
    if (window.g.__current_sequence == 1 && action == 'previous'){
      $("#question-sequence").addClass("animated flash").css('color', 'yellow');
      $("#question-sequence").one(window.g.__animation_events, function(){
        $(this).removeClass().css('color', '');
      });
      return
    } else if (window.g.__current_sequence == window.g.__SESSION_QUESTION_TOTAL && action == 'next'){
      $("#question-total").addClass("animated flash").css('color', 'yellow');
      $("#question-total").one(window.g.__animation_events, function(){
        $(this).removeClass().css('color', '');
      });
      return
    }

    if (action == 'next' ){
      var targeted_sequence = window.g.__current_sequence + 1;
    } else if (action == 'previous' ){
      var targeted_sequence = window.g.__current_sequence - 1;
    }

    // If question sequence has not been loaded yet, prevent
    // and highlight the question-loading spinner
    window.g.__$current_question = $("#question-pool [data-question-sequence=" + targeted_sequence + "]")
    if (!window.g.__$current_question.length){
      _paq.push(['trackEvent', 'show_session', 'navigation', 'navigate-unloaded']);
      toastr.warning("You're super fast, " + window.USER_FIRST_NAME  + "!  Give us a second to bring question #" + targeted_sequence.toString() + ".");
      $("#question-loading").addClass("animated flash").css('color', 'yellow');
      return
    }

    // Upon navigation, hide previous voting tooltips
    $(".check, .answer-correction-notification, .opposing-users, .supporting-users").tooltip('hide');

    showQuestion(targeted_sequence);
}

function toggleSharingResults() {
    if (!window.IS_SHARED || !window.SESSION_MODE == 'EXPLAINED'){
      return
    }
    $.ajax({
        url: Urls['exams:toggle_sharing_results'](),
        type: 'POST',
        data: {session_pk: window.SESSION_PK},
        cache: false,
        success: function(data){
           if (data.share_results){
             var names = [];
             $('.sharer-name').each(function(){
               var session_pk = $(this).closest('.shared-session').find('.progress').data('pk');
               if (session_pk != window.SESSION_PK){
                 names.push(this.innerHTML)
               }
             });
             var joined_names;
             if (names.length > 1){
               var last_name = names.pop();
               joined_names =  names.join(', ') + ' and ' + last_name;
             } else {
               joined_names = names[0];
             }
             toastr.success("Sharing the results of this session with " + joined_names + " has been enabled.");
             _paq.push(['trackEvent', 'show_session', 'share-results', 'enable-sharing']);
             $("#share-results").prop('checked', true);
           } else {
             toastr.success("Sharing the results of this session has been disabled.");
             _paq.push(['trackEvent', 'show_session', 'share-results', 'disable-sharing']);
             $("#share-results").prop('checked', false);
           }
           updateSharedProgressBar(window.SESSION_PK, window.g.__STATS);
        }
    });
}

function toggleMarked() {
    $("#mark-icon").hide();
    $("#mark-loading").css('display', 'inline-block');
    $.ajax({
        url: Urls['exams:toggle_marked'](),
        type: 'POST',
        data: {session_pk: window.SESSION_PK,
               question_pk: window.g.__$current_question.data('question-pk')},
        cache: false,
        success: function(data){
           var question_pk = window.g.__$current_question.data('question-pk'),
               marked_index = window.g.__MARKS.indexOf(question_pk);
           window.g.__$current_question.data('is-marked', data.is_marked);
           handleMarked(data.is_marked);
           if (data.is_marked){
             if (marked_index == -1){
               window.g.__MARKS.push(question_pk)
             }
             _paq.push(['trackEvent', 'show_session', 'mark-question', 'add-mark']);
           } else {
             if (marked_index != -1){
               window.g.__MARKS.slice(marked_index, 1);
             }
             _paq.push(['trackEvent', 'show_session', 'mark-question', 'remove-mark']);
           }

           // If we have a navigation table, let's update it.
           // Otherwise, let's save the DOM queries.
           if (window.g.__HAS_CONSTRUCTED_NAVIGATION){
             var $question_row = $('.navigate-row[data-question-sequence="' + window.g.__current_sequence + '"]');
             if (data.is_marked){
               $question_row.find('td.is_marked').html(window.g.__is_marked_markup);
               if (isSafari9()){
                 FontAwesome.dom.i2svg({node: document.getElementById('navigation-table')});
               }
             } else {
               $question_row.find('td.is_marked').html("");
             }
           }

           $("#mark-icon").show();
           $("#mark-loading").hide();

        }
    });
}

function toggleChoices() {
    var $choice = $(this);
    if ($choice.is(":checked")) {
        // other sister choices to be removed
        var $otherChoices = $choice.closest('.question-body').find('.question-choice').not($choice);
        // If a choice is checked, it is no longer striked.
        if ($choice.closest('tr').find('.choice-text.strike').length){
          $choice.closest('tr').find('.choice-text.strike').removeClass('strike');
          submitHighlight();
        }
        $otherChoices.prop("checked", false);
    } else {
        $choice.prop("checked", false);
    }
}

function removeHighlight(){
  $(this).contents().unwrap();
  submitHighlight();
}

function highlightText() {
    var text = $(this).closest('.selection-hint').data('text');
    if (text.length >= 3) {
        var escapedSelection = $("<div>").text(text).html(),
            replacement = $('<span></span>').addClass('highlight').html(text),
            replacementHtml = replacement.prop('outerHTML'),
            $question_text = window.g.__$current_question.find('.question-text');
        $question_text.html($question_text.html().replace(escapedSelection, replacementHtml));
        submitHighlight();
        removeSelectionHint();
    }

}

// == Start of selection hint ==
// This code was adapted from https://github.com/Kikobeats/tweet-selection
function isRightClick (e) {
  var WHICH_RIGHT_CLICK = 3
  var BUTTON_RIGHT_CLICK = 2
  e = e || window.event
  return e.which === WHICH_RIGHT_CLICK || e.button === BUTTON_RIGHT_CLICK || false
}

var selectionInfo = { mouse: {}, isVisible: false }

function addSelectionHint(text, event) {
    var boxVerticalPosition = selectionInfo.mouse.top - 60,
        boxHorizontalPosition = selectionInfo.mouse.left + (event.clientX - selectionInfo.mouse.left) / 2,
        buttons = '',
        encodedText = encodeURIComponent(text);

    // Add highlight only when approrpiate.
    // Otherwise, show the other buttons.
    if (window.SESSION_IS_EXAMINABLE && !window.g.__$current_question.data('was-solved') || !window.SESSION_IS_EXAMINABLE){
      buttons += '<i class="rounded py-2 fas fa-highlighter highlight-selection"></i>'
    }
    if (text.length <= 40){
       buttons += '<a class="d-inline-block" target="_blank" href="https://duckduckgo.com/?q=' + encodedText + '"><i class="rounded py-2 fas fa-globe duckduckgo"></i></a>'
       buttons += '<a class="d-inline-block" target="_blank" href="https://en.wikipedia.org/wiki/Special:Search/' + encodedText + '"><i class="rounded py-2 fab fa-wikipedia-w wikipedia"></i></a>'
    }
    if (text.indexOf(' ') == -1){
      buttons += '<a class="d-inline-block" target="_blank" href="https://en.wiktionary.org/wiki/Special:Search/' + encodedText + '"><i class="rounded py-2 fas fa-language wiktionary"></i></a>'
    }
    // If no buttons are applicable, abort.
    if (!buttons.length){
      return
    }

    var $tag = $('<p class="selection-hint">' + buttons + '</p>');
    // We use this to utlize the power of jQuery's esacaping.
    $tag.attr('data-text', text);
    $('body').append($tag);

    $('.selection-hint').css({
      position: 'absolute',
      top: boxVerticalPosition,
      left: boxHorizontalPosition
    })
}

function removeSelectionHint () {
  $('.selection-hint').remove()
  document.getSelection().removeAllRanges()
}

// actions when the user starts the selection
$('#question-pool').mousedown(function (event) {
  // take the position of the mouse where the user starts the selection
  // we need this for showing the share button in the middle of the selection
  selectionInfo.mouse.top = event.clientY + window.pageYOffset
  selectionInfo.mouse.left = event.clientX

  // remove share button and the old selection
  // Just if the user clicks the left button of the mouse.
  // For right click we must show the genuine browser menu.
  if (!isRightClick(event) && selectionInfo.isVisible) {
    removeSelectionHint();
    selectionInfo.isVisible = false;
  }
})

// actions when the user ends the selection
$('#question-pool').mouseup(function (event) {
  var textSelected = window.getSelection().toString().trim();

  // go further just if user click is left mouse click and the selection length is grater than 3 characters
  if (textSelected.length > 5 && !isRightClick(event)) {
    addSelectionHint(textSelected, event)
    selectionInfo.isVisible = true
  }
})

// == End of selection hint ==


function updateCorrectionTooltip(html, choice_pk){
  var pk_selector = "[data-choice-pk=" + choice_pk + "]",
      $choice_row = $(".question-body tr" + pk_selector),
      notification = '<i class="fas fa-exclamation-triangle text-warning answer-correction-notification mx-1"></i>';
  $choice_row.data('has-correction', true).attr('data-has-correction', 'true');
  $choice_row.find('.check').html(notification + html);
}

/* This function does not get minified because it is called in
   contribute_mnemonics.html */
function initializeMnemonicInteractions(){
  var question_pk = window.g.__$current_question.data('question-pk');

  window.g.__$current_question.find('.mnemonic').each(function(){
    var $mnemonic = $(this),
        submitter_pk = $mnemonic.data('submitter-pk');
    if (submitter_pk == window.USER_PK){
      $mnemonic.find('.like-mnemonic').attr('disabled', true);
      $mnemonic.find('.delete-mnemonic').removeClass('d-none');
    }
  });

  window.g.__$current_question.find(".like-mnemonic").off('click').on('click', function() {
       var $like = $(this),
           action = $like.data('action'),
           mnemonic_pk = $like.closest('.mnemonic').data('mnemonic-pk'),
           url =  Urls['exams:contribute_mnemonics']() + "?" + $.param({question_pk: question_pk});

       $.ajax({
           url: url,
           type: 'POST',
           data: {'action': action,'mnemonic_pk':mnemonic_pk},
           success: function(data){
             if (data.success == 1){
               toastr.success("Your vote was submitted.");
               window.g.__$current_question.find(".mnemonics-content").html(data.mnemonic_html);
               initializeMnemonicInteractions();
             } else {
               toastr.error(data.message)
             }
           }
       });
  });
  window.g.__$current_question.off('click', ".delete-mnemonic").on('click', ".delete-mnemonic", function() {
       var $delete = $(this),
           action = $delete.data('action'),
           mnemonic_pk = $delete.closest('.mnemonic').data('mnemonic-pk'),
           url = Urls['exams:contribute_mnemonics']() + "?" + $.param({question_pk: question_pk});

       $.ajax({
           url: url,
           type: 'POST',
           data: {'action': action,'mnemonic_pk':mnemonic_pk},
           success: function(data){
             if (data.success == 1){
               toastr.success("Your mnemonic is deleted.");
               window.g.__$current_question.find(".mnemonics-content").html(data.mnemonic_html);
               initializeMnemonicInteractions();
             } else {
               toastr.error(data.message)
             }
           }
       });
  });
}

function initializeCorrectionInteractions(){
  // Here, we are selecting the SVG (i.e. '[data-fa-i2svg]')
  // within the '.correct' cell
  window.g.__$current_question.off('click', '.correct [data-fa-i2svg]')
                            .on('click', '.correct [data-fa-i2svg]', function () {
      _paq.push(['trackEvent', 'show_session', 'answer_correction', 'click-correct']);
      $("#correct-answer-modal").modal('show');
      var choice_pk = $(this).closest('tr').data('choice-pk'),
          url = Urls['exams:correct_answer']() + "?" + $.param({choice_pk: choice_pk});
      $("#correct-answer-modal .modal-body").load(url);
  });
}

function controlExplanation(){
  var has_explanation = window.g.__$current_question.find('.explanation-text').length ||
                        window.g.__$current_question.find('.explanation-figure').length ||
                        window.g.__$current_question.find('.explanation-reference-header').length,
      was_solved = window.g.__$current_question.data('was-solved'),
      $explanation_container = window.g.__$current_question.find(".explanation-container");

  if (!was_solved || (window.SESSION_MODE == 'UNEXPLAINED' && !$('body').data('has-finished'))){
    $explanation_container.hide()
    $("#explain").hide()
  } else if (has_explanation){
    $explanation_container.show();
    $("#explain").show().html('<i class="fas fa-cubes"></i> Improve this explanation!');
  } else {
    $explanation_container.hide();
    $("#explain").show().html("Add an explanation!");
  }
}

function controlMnemonic(){
  var was_solved = window.g.__$current_question.data('was-solved'),
      has_mnemonics = window.g.__$current_question.find('.mnemonic').length;

  if (!was_solved || (window.SESSION_MODE == 'UNEXPLAINED' && !$('body').data('has-finished'))){
    $(".mnemonics-container, #add-mnemonics").hide()
  } else if( has_mnemonics ) {
    $('#add-mnemonics').show().html('<i class="fas fa-book"></i> Add another mnemonic!');
    $(".mnemonics-container").show();
  } else {
    $(".mnemonics-container").hide();
    $('#add-mnemonics').show().html('<i class="fas fa-book"></i> Add the first mnemonic!');
  }
}

function controlSessionFinished(){
  // Check whether we have any unsolved questions. Changing
  // data-has-finished to true will cause expalantions to show
  // right away in UNEXPLAINED sessions.
  // This also affects #results and #end buttons.
  if (window.g.__ANSWERS && Object.keys(window.g.__ANSWERS).length >= window.g.__SESSION_QUESTION_TOTAL){
    $('body').data('has-finished', true).attr('data-has-finished', 'true');
  }
}

function controlNavigationButtons(){
  // In case this is a tablet, we do not want the tooltips
  if (window.g.__isTablet){
    return
  }

  // We dispose in all cases to allow for changes, if indicated,
  // to be applied.
  $("#next").tooltip('dispose');

  if (window.g.__current_sequence == window.g.__SESSION_QUESTION_TOTAL){
    $("#next").css('cursor', 'not-allowed');
    // select whatever button that's visible
    var button_name = $("#end:visible, #results:visible").html();
    $("#next").tooltip({title: 'This is the last question.  You can click <kbd>' + button_name + '</kbd> to end this session.',
                        html: true,
                        sanitize: false})
  } else {
    $("#next").tooltip({sanitize: false});
    $("#next").css('cursor', 'pointer');
  }

  if (window.g.__current_sequence == 1){
    $("#previous").css('cursor', 'not-allowed');
  } else {
    $("#previous").css('cursor', 'pointer');
  }
}

function highlightActiveRow(){
  // Mark row as active
  var $question_row = $('.navigate-row[data-question-sequence="' + window.g.__current_sequence + '"]');
  $question_row.addClass('table-active');
  $('.navigate-row').not($question_row).removeClass('table-active');
}

function disableHighlightInteractions(){
  window.g.__$current_question.off('click', '.highlight')
  window.g.__$current_question.find(".choice-text").off('click')
  window.g.__$current_question.find(".question-text").off('mouseup touchend')
}

function initializeInteractions() {
    // $current_question is defined in showQuestion
    window.g.__$current_question.find('[data-toggle="tooltip"]').tooltip();

    initializeCorrectionInteractions();
    initializeMnemonicInteractions();
    controlNavigationButtons();
    handleMarked(window.g.__$current_question.data('is-marked'));

    // If we have a navigation table, let's update it.
    // Otherwise, let's save the DOM queries.
    if (window.g.__HAS_CONSTRUCTED_NAVIGATION){
      highlightActiveRow();
    }

    // Show contributors as a tooltip
    $("#contributors").tooltip('dispose');
    $("#contributors").off('click').click(function(){
        _paq.push(['trackEvent', 'show_session', 'see-contributors', 'see-contributors']);
    });
    $("#contributors").tooltip({html: true,
                                sanitize: false,
                                trigger: 'click',
                                title: window.g.__$current_question.find(".tooltip-body").get(0)})

    // Disable interaction if question was solved.

    controlExplanation();
    controlMnemonic();
    var was_solved = window.g.__$current_question.data('was-solved');

    if (was_solved){
      $("#contribute,#add-mnemonics").show();
      window.g.__$submitButton.hide();
      window.g.__$current_question.find(".question-choice").prop("disabled", "disabled");
    } else {
        $("#contribute,#add-mnemonics").hide();
        window.g.__$submitButton.show();
        window.g.__$current_question.find(".question-choice").off('change').on('change', toggleChoices);
    }

    // We want to enable highlight in two cases:
    // 1) If the session is examinable, and the current question was NOT solved.
    // 2) If the session is not examinable.
    if (window.SESSION_IS_EXAMINABLE && !was_solved || !window.SESSION_IS_EXAMINABLE){
      window.g.__$current_question.find(".choice-text").off('click').on('click', function() {
          if (!$(this).hasClass("strike")){
             // If a choice is striked, it is no longer checked.
              $(this).closest("tr").find(".question-choice").prop('checked', false).trigger('change');
          }
          $(this).toggleClass("strike");
          submitHighlight();
      });
    } else {
      disableHighlightInteractions();
    }
}

function submitHighlight(){
  var stricken_choice_pks = window.g.__$current_question.find(".choice-text.strike").map(function(){return $(this).closest('tr').data('choice-pk')}).get();
  stricken_choice_pks = JSON.stringify(stricken_choice_pks);

  var data = {best_revision_pk: window.g.__$current_question.data('best-latest-revision-pk'),
              highlighted_text: window.g.__$current_question.find(".question-text").html(),
              stricken_choice_pks: stricken_choice_pks,
              session_pk: window.SESSION_PK,
              question_pk: window.g.__$current_question.data('question-pk')}

  $.ajax({
      url: Urls['exams:submit_highlight'](),
      type: 'POST',
      data: data
  });
}

function submitChoice() {
    $(this).hide();

    // if question was previously solved, don't submit.
    if (window.g.__$current_question.data('was-solved')){
      return
    }
    // Mark question as solved
    // We also set was-solved using .attr() to change the DOM and
    // be able to apply CSS.
    window.g.__$current_question.data('was-solved', true).attr('data-was-solved', 'true');


    // If we have a navigation table, let's update it.
    // Otherwise, let's save the DOM queries.
    if (window.g.__HAS_CONSTRUCTED_NAVIGATION){
      var $question_row = $('.navigate-row[data-question-sequence="' + window.g.__current_sequence + '"]');
      $question_row.find('td.was_solved').html(window.g.__was_solved_markup);
      if (isSafari9()){
        FontAwesome.dom.i2svg({node: document.getElementById('navigation-table')});
      }
    }

    // Disable choices upon submission
    window.g.__$current_question.find(".question-choice").prop("disabled", "disabled")
    // Disable interactions after submission.
    controlExplanation();
    controlMnemonic();
    disableHighlightInteractions();
    $("#contribute,#add-mnemonics").show();
    window.g.__$current_question.find(".question-text, .question-choice, .choice-text").off();

    var $checkedChoice = window.g.__$current_question.find(".question-choice:checked");

    // Do we have a choice, or was it skipped?
    if ($checkedChoice.length) {
        // We store choice pk at the row.
        var $choice_row = $checkedChoice.closest('tr'),
            choice_pk = $choice_row.data("choice-pk");

        // If there is a correction, we invite the user to vote:
        if ($choice_row.data('is-right')){
          window.g.__STATS.correct_count += 1
        } else {
          window.g.__STATS.incorrect_count += 1
        }
        var $correction_notification = $choice_row.find('.answer-correction-notification')
        // Let's ensure that the support voting button is enabled
        // (i.e. the user is not the submitter of the correction
        // or a previous voter)
        var $support_button = $choice_row.find('button.support-correction:enabled')
        if ($correction_notification.length && $support_button.length && !(window.SESSION_MODE == 'UNEXPLAINED' && !$('body').data('has-finished'))){
          $choice_row.find('.check').tooltip({template: '<div class="tooltip hint" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>',
                                              html: true,
                                              sanitize: false,
                                              title:"<strong>Are you sure that this is the right answer?</strong>  Vote to support this correction! <img height=\'17\' src=\'https://cdnjs.cloudflare.com/ajax/libs/emojione/2.2.7/assets/png/1f64a.png\'>",
                                              placement: 'right',
                                              trigger: 'manual'}).tooltip('show');
          setTimeout(function(){$choice_row.find('.check').tooltip('hide')}, 5000);
        }
    } else {
        window.g.__STATS.skipped_count += 1
        var choice_pk = null;
    }

    updateSharedProgressBar(window.SESSION_PK, window.g.__STATS);

    var question_pk = window.g.__$current_question.data('question-pk')
    window.g.__ANSWERS[question_pk] = choice_pk;
    controlSessionFinished();

    var data = {session_pk: window.SESSION_PK,
                question_pk: question_pk,
                choice_pk: choice_pk}

    $.ajax({
        url: Urls['exams:submit_answer'](),
        type: 'POST',
        data: data,
        cache: false,
        success: function(data) {
            if (data.success) {
                if (!choice_pk){
                    toastr.warning('You skipped this question');
                }
            } else {
              toastr.error(data.message);
            }
        }
    });

}

function updateSizes() {
  // The question row should take all the space not taken by other elements
  var row_height = $("#container").height() - $('#top-info').height() - $('#top-options').height();
  $("#question-row").css({
    'padding-bottom': $('#footer').height(),
    'min-height': row_height
  });
}

function initializeKeyboard(){
  $(document).keydown(function(e){
    // record active keys so we can handle a combination of keys
    window.g.__active_keys[e.which] = true;

    // check which key we got
    if (window.g.__active_keys[37]) { // left key
      $("#previous").trigger('click');
      _paq.push(['trackEvent', 'show_session', 'navigation', 'keyboard-previous']);
    } else if (window.g.__active_keys[39] || window.g.__active_keys[32]) {  // right key or space
      e.preventDefault() // prevent space scroll.
      $("#next").trigger('click');
      _paq.push(['trackEvent', 'show_session', 'navigation', 'keyboard-next']);
    } else if (window.g.__active_keys[18] && window.g.__active_keys[77]) { // alt + m
      _paq.push(['trackEvent', 'show_session', 'mark-question', 'keyboard-mark']);
      window.g.__$markButton.trigger('click');
    } else if (window.g.__active_keys[18] && window.g.__active_keys[85]) { // alt + u
      _paq.push(['trackEvent', 'show_session', 'find-pending', 'keyboard-pending']);
      if (window.SESSION_MODE == 'SOLVED' || window.SESSION_MODE == 'INCOMPLETE'){
        return
      }
      var question_sequence = $('.question-body[data-was-solved=false]').data('question-sequence');
      if (question_sequence){
        showQuestion(question_sequence);
      } else {
        toastr.success("Yay!  No pending in this session.");
      }
    } else if (window.g.__active_keys[17] && window.g.__active_keys[13]) { // ctrl + enter
      _paq.push(['trackEvent', 'show_session', 'mark-question', 'keyboard-submit']);
      window.g.__$submitButton.trigger('click');
    } else if (window.g.__active_keys[17] && window.g.__active_keys[38] || window.g.__active_keys[17] && window.g.__active_keys[40]){ // ctrl + up or ctrl + down
      e.preventDefault() // prevent arrow scroll.
      var total_choices = window.g.__$current_question.find(".question-choice").length,
          $checked_choice = window.g.__$current_question.find(".question-choice:enabled:checked")
      if ($checked_choice.length){
        var choice_index = window.g.__$current_question.find(".question-choice").index($checked_choice);
        if (window.g.__active_keys[38] && choice_index == 0){ // Up while at top
          // We are at the topmost choice, we cannot go up.
          return
        } else if (window.g.__active_keys[40] && choice_index == (total_choices -1)){ // Up while at bottom
          // We are at the bottom most choice, we cannot go futher down
          return
        } else {
          if (window.g.__active_keys[40]){ // down
            _paq.push(['trackEvent', 'show_session', 'navigation', 'keyboard-down']);
            var target_index = choice_index + 1
          } else if (window.g.__active_keys[38]){ // up
            _paq.push(['trackEvent', 'show_session', 'navigation', 'keyboard-up']);
            var target_index = choice_index - 1;
          }
        }
      } else {
        // If no choice is already checked, arrows always select the first choice.
        var target_index = 0;
      }
      var target_choice = window.g.__$current_question.find('.question-choice:enabled').get(target_index)
      $(target_choice).prop('checked', true).trigger('change');
    } else {
      // If no matching keyboard shortcut, do not execuse
      // upcoming code snippet
      return
    }
  });
  $(document).keyup(function (e) {
      // remove keys that are no longer active;
      delete window.g.__active_keys[e.which];
  });
}

function constructNavigationTable(){
  // the navigation modal is special in that it is closed by
  // keyboard and by clicking the backdrop
  $('#navigate-modal').modal({show: false});
  $("#open-navigation").off('click').click(function(){
    _paq.push(['trackEvent', 'show_session', 'navigation', 'open-navigation']);
    $('#navigate-modal').modal('show')
  });

  // move to the position of the active row
  $('#navigate-modal').on('shown.bs.modal', function (){
     $(this).animate({
         scrollTop: $(".navigate-row.table-active").position().top
     }, 500);
  });

  // Let's not use jQuery.  It's too slow for constructing massive elements.
  var tbody = document.getElementById("navigation-tbody"),
      tbody_content = "";

  for (var question_sequence = 1; question_sequence <= window.g.__SESSION_QUESTION_PKS.length; question_sequence++) {
     var question_index = question_sequence - 1,
         question_pk = window.g.__SESSION_QUESTION_PKS[question_index],
         was_solved = window.g.__ANSWERS[question_pk] !== undefined ? window.g.__was_solved_markup : '<i class="far fa-square"></i>';
     // In case MARKS was not populated yet, we can safely skip
     // it.
     if (window.g.__MARKS){
       var is_marked = window.g.__MARKS.indexOf(question_pk) != -1 ? window.g.__is_marked_markup : '';
     }
     var row = "<tr tabindex='0' class='navigate-row text-center' data-question-sequence='" + question_sequence.toString() + "'><td>" + question_sequence.toString() + "</td><td class='d-sm-table-cell d-none'>" + question_pk.toString() + "</td><td class='d-sm-table-cell d-none is_marked'>" + is_marked + "</td><td class='was_solved'>" + was_solved +"</td></tr>";
     tbody_content += row;
  }

  tbody.innerHTML = tbody_content;

  if (isSafari9()){
    FontAwesome.dom.i2svg({node: document.getElementById('navigation-table')})
  }

  $("#navigation-table").find('.navigate-row').click(function(){
    _paq.push(['trackEvent', 'show_session', 'navigation', 'click-navigate-row']);
    var targeted_sequence = $(this).data('question-sequence');
    showQuestion(targeted_sequence);
  });
  highlightActiveRow();
  window.g.__HAS_CONSTRUCTED_NAVIGATION = true;
}

function fetchAnswers(){
  $.ajax({method: 'get',
          url: Urls['answer-list'](),
          data: {format: 'json',
                 session_pk: window.SESSION_PK },
          success: function(data){
              window.g.__ANSWERS = {};
              window.g.__STATS = {correct_count: 0,
                                  incorrect_count: 0,
                                  skipped_count: 0,};
              data.map(function(item){
                if (item.choice === null){
                  window.g.__STATS.skipped_count += 1
                  window.g.__ANSWERS[item.question_id] = null;
                } else if (item.choice.is_right === true){
                  window.g.__STATS.correct_count += 1
                  window.g.__ANSWERS[item.question_id] = item.choice.id;
                } else if (item.choice.is_right === false){
                  window.g.__STATS.incorrect_count += 1
                  window.g.__ANSWERS[item.question_id] = item.choice.id;
                }
              });

              // We can only prepare questions after we get
              // ANSWERS, so let's do it now!
              prepareQuestions($('.question-body'));
              // Some interactions depend on whether the question
              // was solved or not.  That's why we only
              // initialize interactions after we have prepared
              // the questions.
              controlSessionFinished();
              updateSharedProgressBar(window.SESSION_PK, window.g.__STATS);
              initializeInteractions();
              $("#open-navigation").tooltip('dispose').css('cursor', 'pointer').click(function(){
                constructNavigationTable();

                $(this).trigger('click');
              });
          }
  });
}

function fetchMarks(){
  $.ajax({method: 'get',
          url: Urls['marked-list'](),
          data: {format: 'json',
                 exam_pk: window.EXAM_PK },
          success: function(data){
              window.g.__MARKS = data.map(function(item){ return item.id });

              $('.question-body').each(function(){
                var $question = $(this),
                    question_pk = $question.data('question-pk');
                applyMark($question, question_pk);
              });
          }
  });
}


function fetchHighlights(){
  $.ajax({method: 'get',
          url: Urls['highlight-list'](),
          data: {format: 'json',
                 session_pk: window.SESSION_PK },
          success: function(data){
              window.g.__PREVIOUS_HIGHLIGHTS = {};
              data.map(function(item){
                window.g.__PREVIOUS_HIGHLIGHTS[item.revision.question_id] = {revision_id: item.revision.id,
                                                         highlighted_text: item.highlighted_text,
                                                         stricken_choices: item.stricken_choices};
              });

              $('.question-body').each(function(){
                var $question = $(this);
                prepareHighlights($question);
              });
          }
  });
}

function fetchSharedStats(){
  // If the current session hasn't been initialized, abort this trial;
  if (!window.g.__$current_question){
    return
  }
  // Prevent overlapping requests.
  clearSharedStatTimer();
  if (window.g.__IS_PRESENTER) {
    var question_pk = window.g.__$current_question.data('question-pk');
  } else {
    var question_pk = null;
  }
  $.ajax({method: 'get',
          url: Urls['exams:get_shared_session_stats'](),
          data: {format: 'json',
                 session_pk: window.SESSION_PK,
                 question_pk: question_pk},
          success: function(data){
            if (data.success){
              for (var index in data.stats.sessions){
                var stat = data.stats.sessions[index];
                updateSharedProgressBar(stat.pk, stat)
              }
              if (window.g.__IS_PRESENTER){
                window.g.__chart.data.datasets[0].data = data.stats.choices;
                window.g.__chart.update();
              }
              if (!$('.progress[data-has-finished="false"]').length){
                clearSharedStatTimer();
              }
            } else {
              toastr.error(data.message)
            }
          }
  });
  // Re-enable the timer;
  setSharedStatTimer();
}

function updateSharedProgressBar(session_pk, stat){
  if (!window.IS_SHARED){
    return
  }

  var $shared_session_container = $("#shared-session-" + session_pk),
      $progress_container = $shared_session_container.find('.progress');

  if (session_pk != window.SESSION_PK){
    $progress_container.attr('data-has-finished', stat.has_finished.toString());
  } else if (session_pk == window.SESSION_PK && (window.SESSION_MODE != 'EXPLAINED' || !$('#share-results').prop('checked'))){
    stat.count = stat.correct_count + stat.incorrect_count + stat.skipped_count;
  } else {
    delete stat.count;
  }

  // Only detail the breakdown if the session mode is EXPLAINED.
  // Otherwise, only show a generic count.
  $shared_session_container.tooltip('dispose');
  if (stat.count){
    var percentage = Math.round(stat.count / window.g.__SESSION_QUESTION_TOTAL * 100) + '%';
    $progress_container.html('<div class="progress-bar bg-success" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + stat.count + '" style="width: ' + percentage + '"></div>');
    $shared_session_container.tooltip({html: true, title: '<span class="sharer-name">' + stat.count + " out of " + window.g.__SESSION_QUESTION_TOTAL + " questions (" + percentage + ")</span>"});
  } else {
    var correct_percentage = Math.round(stat.correct_count / window.g.__SESSION_QUESTION_TOTAL * 100) + '%',
        incorrect_percentage = Math.round(stat.incorrect_count / window.g.__SESSION_QUESTION_TOTAL * 100) + '%',
        skipped_percentage = Math.round(stat.skipped_count / window.g.__SESSION_QUESTION_TOTAL * 100) + '%';
    $progress_container.html('<div class="progress-bar bg-success" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + stat.correct_count + '" style="width: ' + correct_percentage + '"></div>' +
                             '<div class="progress-bar bg-danger" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + stat.incorrect_count + '" style="width: ' + incorrect_percentage + '"></div>' +
                             '<div class="progress-bar bg-warning" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + stat.skipped_count + '" style="width: ' + skipped_percentage + '"></div>')
    $shared_session_container.tooltip({html: true, title: '<ul class="mb-0 pl-3 sharer-name"><li>Correct: ' + stat.correct_count + ' (' + correct_percentage +')</li><li>Incorrect: ' + stat.incorrect_count + ' (' + incorrect_percentage + ')</li><li>Skipped: ' + stat.skipped_count + ' (' + skipped_percentage +')</li></ul>'})
  }

}

function isSafari9(){
  // This is a workaround for iOS 9.x browsers that
  // cannot render dynmically added FontAwesome icons.
  return ((navigator.userAgent.indexOf('iPhone') != -1 ||
           navigator.userAgent.indexOf('iPad') != -1) &&
          navigator.userAgent.indexOf('OS 9_') != -1) ||
         (navigator.userAgent.indexOf('Mac OS') != -1 &&
          navigator.userAgent.indexOf('Version/9') != -1 &&
          navigator.userAgent.indexOf('Safari/') != -1)
}

function fetchList(fetch_list_index, question_sequence){
  // If the given index was previously fetched, skip!
  if (window.g.__fetched_indexes.indexOf(fetch_list_index) != -1){
    return
  }

  var current_targets = window.g.__SESSION_QUESTION_PKS.slice(fetch_list_index, fetch_list_index + 50),
      current_target_str = current_targets.join(',');
  $("#question-loading").show();

  $.ajax({method: 'get',
          url: Urls['exams:list_partial_session_questions'](window.CATEGORY_SLUGS, window.EXAM_PK),
          data: {pks: current_target_str},
          success: function(data){
            window.g.__fetched_indexes.push(fetch_list_index);

            var $questions = $(data.html);

            // Do not bother with filtering except if we know
            // that we need it.
            if (current_targets.indexOf(window.g.__initial_question_pk) != -1){
              var $filtered_questions = $questions.filter(function(){
                var $question = $(this),
                    question_pk = $question.data('question-pk');
                return question_pk != window.g.__initial_question_pk
              });
            } else {
              var $filtered_questions = $questions
            }

            prepareQuestions($filtered_questions);

            $("#question-pool").append($filtered_questions);

            $.ajax({method: 'get',
                    url: Urls['correction-list'](),
                    data: {format: 'json',
                           exam_pk: window.EXAM_PK,
                           question_pks: current_target_str},
                    success: function(data){
                        $.each(data, function(index, correction){
                          updateCorrectionTooltip(correction.html, correction.choice_id)
                        });
                    }
            });

            if (isSafari9()){
              FontAwesome.dom.i2svg({node: document.getElementById('question-pool')})
            }

            if (question_sequence){
              showQuestion(question_sequence);
            }
            $("#question-loading").hide();
          }
  });
}

function prepareHighlights($question) {
  // If we do not have the PREVIOUS_HIGHLIGHTS yet, we cannot
  // prepare the highlights.
  if (window.g.__PREVIOUS_HIGHLIGHTS === null){
    return
  }

  var question_pk = $question.data('question-pk'),
      highlight = window.g.__PREVIOUS_HIGHLIGHTS[question_pk];
  if (highlight !== undefined){
    var best_revision_pk = $question.data('best-latest-revision-pk');
    if (best_revision_pk == highlight.revision_id){
      // If the highlighted question text is not empty, include
      // it.
      if (highlight.highlighted_text){
        $question.find('.question-text').html(highlight.highlighted_text);
      }
      $.each(highlight.stricken_choices, function(index){
        var choice_pk = highlight.stricken_choices[index];
        $question.find('tr[data-choice-pk=' + choice_pk + '] .choice-text').addClass('strike');
      });
    }
  }
}

function prepareChoices($question) {
  // This shuffle choices and checked the previously selected
  // choice and randomizes choice rows.

  // If we do not have the ANSWERS yet, we cannot prepare the
  // choices.
  if (window.g.__ANSWERS === null){
    return
  }

  // First: Tag the previously selected choice:
  var question_pk = $question.data('question-pk'),
      choice_pk = window.g.__ANSWERS[question_pk];
  if (choice_pk !== undefined){
    $question.data('was-solved', true).attr('data-was-solved', 'true')
    $question.find('.question-choice').attr('disabled', true)

    // If question was not skipped (not null)
    if (choice_pk){
      var $checkbox = $question.find('tr[data-choice-pk=' + choice_pk + '] input[type="checkbox"]');
      $checkbox.prop('checked', true)
    }
  } else {
    $question.data('was-solved', false).attr('data-was-solved', 'false')
  }

  // Second: randomizes choice rows
  var $tbody = $question.find('.choice-table tbody'),
      $choice_rows = $tbody.find('tr'),
      currentIndex = $choice_rows.length,
      temporaryValue,
      randomIndex;

  // Based on https://stackoverflow.com/a/2450976
  $choice_rows.detach()

  // While there remain elements to shuffle...
  while (0 !== currentIndex) {

    // Pick a remaining element...
    randomIndex = Math.floor(Math.random() * currentIndex);
    currentIndex -= 1;

    // And swap it with the current element.
    temporaryValue = $choice_rows[currentIndex];
    $choice_rows[currentIndex] = $choice_rows[randomIndex];
    $choice_rows[randomIndex] = temporaryValue;
  }

  $tbody.append($choice_rows)
  // We use the 'unrandomized' class to hide the choices until
  // they are randomized to avoid confusing layout changes
  $tbody.removeClass('unprepared')

}

function applyMark($question, question_pk){
  if (window.g.__MARKS.indexOf(question_pk) != -1){
    $question.data('is-marked', true).attr('data-is-marked', 'true')
    // If the marked question is currently being shown, highlight
    // the mark button.
    if ($question.hasClass('show')){
      handleMarked(true)
    }
  } else {
    $question.data('is-marked', false).attr('data-is-marked', 'false')
  }
}

// Client-side work-up
function prepareQuestions($questions){
  $questions.each(function(){
    var $question = $(this),
        question_pk = $question.data('question-pk'),
        question_text = $question.find('.question-text').html(),
        explanation_text = $question.find('.explanation-text').html(),
        question_html = converter.makeHtml(question_text); // Parse markdown
    $question.find('.question-text').html(question_html);

    if (explanation_text !== undefined){
      var explanation_html = converter.makeHtml(explanation_text);
      $question.find('.explanation-text').html(explanation_html);
    }

    prepareChoices($question);
    prepareHighlights($question);

    // Add sequence
    var question_sequence = window.g.__SESSION_QUESTION_PKS.indexOf(question_pk) + 1;
    $question.data('question-sequence', question_sequence).attr('data-question-sequence', question_sequence);

    // Add url data tags
    var list_revision_url = Urls['exams:list_revisions'](window.CATEGORY_SLUGS, window.EXAM_PK, question_pk);
    var question_url = Urls['exams:show_session'](window.CATEGORY_SLUGS, window.EXAM_PK, window.SESSION_PK, question_pk);
    $question.data('list-revision-url', list_revision_url).attr('data-list-revision-url', list_revision_url);
    $question.data('url', question_url).attr('data-url', question_url);

    if (window.SESSION_MODE == 'SOLVED' || window.SESSION_MODE == 'INCOMPLETE'){
      $question.data('was-solved', true).attr('data-was-solved', 'true')
      $question.find('.question-choice').attr('disabled', true)
    }

    if (window.g.__MARKS){
      applyMark($question, question_pk);
    }
  });

  var $question_pool = $('#question-pool');
  if (!$question_pool.hasClass('choices-were-animated')){
    $question_pool.addClass('choices-were-animated')
    window.g.__$current_question.find('tbody').addClass('animated fadeIn').one(window.g.__animation_events, function(){$(this).removeClass()});
  }
}

function setSharedStatTimer(){
  if (!window.g.__SHARED_STAT_TIMER && document.hasFocus() && $('.progress[data-has-finished="false"]').length){
    var timeout = window.g.__IS_PRESENTER ? 2000 : 5000;
    window.g.__SHARED_STAT_TIMER = setInterval(fetchSharedStats, timeout);
  }
}

function clearSharedStatTimer(){
    if (window.g.__SHARED_STAT_TIMER){
      clearInterval(window.g.__SHARED_STAT_TIMER);
      window.g.__SHARED_STAT_TIMER = null;
    }
}

// Show mobile sliders in tablets
if (window.g.__isTablet){
  $('.mobile-slide').removeClass('d-lg-none');
  $('#question-col').removeClass('col-lg-12 px-lg-5');
}

// Do not show keyboard-hint in tablets or mobile phones.
if (window.g.__isTablet || window.g.__isMobile){
  $('#keyboard-hint').addClass('d-none');
}

$(function() {
    var copy_share = new ClipboardJS('#share-session-copy');
    copy_share.on('success', function(e){
      _paq.push(['trackEvent', 'show_session', 'share', 'click-copy']);
      $(e.trigger).tooltip('show'); setTimeout(function(){$(e.trigger).tooltip('hide')}, 1000)
    });

    var $initial_question = $('.question-body.show');

    // Set sequence for initial question
    window.g.__initial_question_pk = $initial_question.data('question-pk');
    var initial_question_sequence = window.g.__SESSION_QUESTION_PKS.indexOf(window.g.__initial_question_pk) + 1;
    $initial_question.attr('data-question-sequence', initial_question_sequence).data('question-sequence', initial_question_sequence)

    // Show initial question
    showQuestion(initial_question_sequence, true);

    $("#question-total").html(window.g.__SESSION_QUESTION_TOTAL);
    $("#question-sequence").html(initial_question_sequence);

    initializeKeyboard();

    if (window.IS_SHARED){
      $(window).on('focus', function(){
        if ($('.progress[data-has-finished="false"]').length){
          fetchSharedStats();
        }
        setSharedStatTimer();
      });
      $(window).on('blur', clearSharedStatTimer);
    }

    // Depending on user agent, we control tooltip initalization.
    // Note that this must NOT be overridden anywhere in the
    // code.  Tooltip intialization always has to be limited to
    // specific subelements of a context
    if (window.g.__isTablet){
      // In tablets, we don't want to show tooltips on the
      // 'Mark' button as well as navigation buttons.
      $('[data-toggle="tooltip"]').not("#next, #previous, #mark").tooltip({sanitize: false});
    } else if (window.g.__isMobile) {
      // In mobile phones, we don't want to show a tooltip on the
      // 'Mark' button
      $('[data-toggle="tooltip"]').not(window.g.__$markButton).tooltip({sanitize: false});
    } else {
      $('[data-toggle="tooltip"]').tooltip({sanitize: false});
    }

    var help_me_tooltip = $("#help-me-tooltip").get(0);
    $("#help-me").tooltip({html: true,
                           trigger: 'click',
                           title: help_me_tooltip})
     $("#help-me").click(function(){
       _paq.push(['trackEvent', 'show_session', 'click-get-help', 'click-get-help']);
     });

     var setting_tooltip = $("#setting-tooltip").get(0);
     $("#settings").tooltip({html: true,
                             placement: 'bottom',
                             trigger: 'click',
                             title: setting_tooltip})
      $("#settings").click(function(){
        _paq.push(['trackEvent', 'show_session', 'click-settings', 'click-settings']);
      });

      var share_tooltip = $("#share-tooltip").get(0);
      $("#share").tooltip({html: true,
                           trigger: 'click',
                           title: share_tooltip})
       $("#share").click(function(){
         $(this).removeClass('emphasized')
         _paq.push(['trackEvent', 'show_session', 'share', 'click-share']);
       });

      $("#theme-select").change(function(){
        var $option = $(this).find('option:selected');
        $(":root").css({'--primary-background-color': $option.data('primary-background-color'),
                        '--secondary-background-color': $option.data('secondary-background-color'),
                        '--tertiary-background-color': $option.data('tertiary-background-color'),
                        '--primary-font-color': $option.data('primary-font-color'),
                        '--secondary-font-color': $option.data('secondary-font-color'),
                        '--tertiary-font-color': $option.data('tertiary-font-color'),
                        '--highlight-background': $option.data('highlight-background'),
                        '--highlight-color': $option.data('highlight-color'),
                        '--table-active': $option.data('table-active'),
                        '--table-hover': $option.data('table-hover')})
      });
      $("#save-theme").click(function(){
        $.ajax({url: Urls['exams:update_session_theme'](),
                type: 'POST',
                data: {session_theme_pk: $("#theme-select").val()},
                success: function(data){
                  if (data.success){
                    $("#settings").tooltip('hide')
                    toastr.success("Your theme was updated!")
                  } else {
                    toastr.error(data.message)
                  }
                }
        });
      });

     fetchAnswers();
     fetchHighlights();
     fetchMarks();
     updateSizes();
     $(window).resize(updateSizes);

     if (window.IS_SHARED){
       fetchSharedStats();
       setSharedStatTimer();
       $("#share-results").change(toggleSharingResults);
     }

     $(".mobile-slide").click(function(){
      if ($(this).hasClass('previous')){
        $("#previous").trigger('click');
        _paq.push(['trackEvent', 'show_session', 'navigation', 'slide-previous']);
      } else if ($(this).hasClass('next')){
        $("#next").trigger('click');
        _paq.push(['trackEvent', 'show_session', 'navigation', 'slide-next']);
      }
    });

    $("#end").click(function(){
      $("#confirm-end-modal a.submit-button").prop("href", Urls['exams:show_session_results'](window.CATEGORY_SLUGS, window.EXAM_PK, window.SESSION_PK));
      $("#confirm-end-modal").modal('show');
    });
    window.g.__$submitButton.click(submitChoice);
    $('#previous, #next').click(navigate);
    window.g.__$markButton.click(toggleMarked);


    // Actions are delegated are defined here.
    $(document).on('click', '.wikipedia, .duckduckgo, .wiktionary', function(){
      var text = $(this).closest('.selection-hint').data('text'),
          action = $(this).hasClass('wikipedia')? 'wikipedia' : ($(this).hasClass('duckduckgo')? 'duckduckgo' : 'wiktionary');
      _paq.push(['trackEvent', 'show_session', action, text]);
    });
    $(document).on('click', '.highlight-selection', highlightText);
    $(document).on('click', '.highlight', removeHighlight);
    $(document).tooltip({selector: '.answer-correction-notification',
                         html: true,
                         trigger: 'click',
                         title: function(){
                             var $tooltip = $(this).closest("td").find('.answer-correction-tooltip-body').clone(true);
                             $tooltip.find('[data-toggle="tooltip"]').tooltip();
                             return $tooltip.get(0)
                         }
    });
    $(document).on('show.bs.tooltip', '.answer-correction-notification', function(){
        $('.answer-correction-notification').not(this).tooltip('hide');
        _paq.push(['trackEvent', 'show_session', 'answer_correction', 'click-notification']);
    });
    $(document).on('click', '.delete-correction', function(){
      var choice_pk = $(this).data('choice-pk'),
          url = Urls['exams:delete_correction']() + "?" + $.param({choice_pk: choice_pk}),
          pk_selector = "[data-choice-pk=" + choice_pk + "]",
          $choice_row = window.g.__$current_question.find("tr" + pk_selector);
      $choice_row.data('has-correction', false).attr('data-has-correction', 'false');
      $('.answer-correction-notification').tooltip('hide');
      $(this).tooltip('hide');

      $.ajax({
          url: url,
          type: 'POST',
          success: function(data){
            if (data.success == 1){
              toastr.success("Your correction was removed.")
              if (data.correction_html){ // if we have a new submitter
                updateCorrectionTooltip(data.correction_html, choice_pk);
              } else {
                // Before there was a correction, it was marked as a wrong answer
                $choice_row.find('.check').html(window.g.__wrong_answer_markup);
              }
            } else {
              toastr.error(data.message)
            }
          }
      });
    });

    $(document).on('click', ".support-correction, .oppose-correction", function(){
      var action = $(this).data('action'),
          choice_pk = $(this).data('choice-pk'),
          url = Urls['exams:correct_answer']() + '?' + $.param({choice_pk: choice_pk})
      _paq.push(['trackEvent', 'show_session', 'answer_correction', 'delete-notification']);

      $.ajax({
          url: url,
          type: 'POST',
          data: {'action': action},
          success: function(data){
            if (data.success == 1){
              toastr.success("Your vote was submitted.")
              updateCorrectionTooltip(data.correction_html, choice_pk);
            } else {
              toastr.error(data.message)
            }
          }
      });
    });

        // initialize project edit modal
    $('#modify-question-modal, #explain-question-modal,#add-mnemonics-modal').modal({
      keyboard: false,
      backdrop: 'static',
      show    : false,
    });

    $("#contribute").click(function () {
        $("#modify-question-modal").modal('show');
        var url = Urls['exams:contribute_revision']() + "?" + $.param({question_pk: window.g.__$current_question.data('question-pk')});
        $("#modify-question-modal .modal-body").load(url);
    });
    // initialize project edit modal
    $("#explain, a.explain").click(function () {
        $("#explain-question-modal").modal('show');
        var url = Urls['exams:contribute_explanation']() + "?" + $.param({question_pk: window.g.__$current_question.data('question-pk')});
        $("#explain-question-modal .modal-body").load(url);
    });

    $("#add-mnemonics").click(function () {
        $("#add-mnemonics-modal").modal('show');
        var url =  Urls['exams:contribute_mnemonics']() + "?" + $.param({question_pk: window.g.__$current_question.data('question-pk')});
        $("#add-mnemonics-modal .modal-body").load(url);
    });

    var modal_selectors = '#explain-question-modal,#modify-question-modal,#correct-answer-modal,#add-mnemonics-modal';

    $(modal_selectors).on("hidden.bs.modal", function(){
      initializeKeyboard();
    });

    $(modal_selectors).on("show.bs.modal", function(){
      $(document).off('keydown keydup');
    });
});

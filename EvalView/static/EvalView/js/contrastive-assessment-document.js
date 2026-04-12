/**
 * Contrastive 3-way assessment JavaScript
 * Handles contrastive submission with single button per row for 3 translations
 */

// Function to submit all three translations in a contrastive row
function submit_contrastive_row($row, $itemBox1, $itemBox2, $itemBox3) {
    // Set end timestamp for all three
    var timestamp = Date.now() / 1000.0;
    $itemBox1.find('input[name="end_timestamp"]').val(timestamp);
    $itemBox2.find('input[name="end_timestamp"]').val(timestamp);
    $itemBox3.find('input[name="end_timestamp"]').val(timestamp);

    // Get form data from all three item-boxes
    var form1 = $itemBox1.find('form');
    var form2 = $itemBox2.find('form');
    var form3 = $itemBox3.find('form');

    // Build combined data
    var data = {};

    // Parse form1 data
    form1.serializeArray().forEach(function(field) {
        if (field.name === 'score') {
            data['score1'] = field.value;
        } else if (field.name === 'mqm') {
            data['mqm1'] = field.value;
        } else if (field.name !== 'ajax') {
            data[field.name] = field.value;
        }
    });

    // Parse form2 data (only score and mqm)
    form2.serializeArray().forEach(function(field) {
        if (field.name === 'score') {
            data['score2'] = field.value;
        } else if (field.name === 'mqm') {
            data['mqm2'] = field.value;
        }
    });

    // Parse form3 data (only score and mqm)
    form3.serializeArray().forEach(function(field) {
        if (field.name === 'score') {
            data['score3'] = field.value;
        } else if (field.name === 'mqm') {
            data['mqm3'] = field.value;
        }
    });

    // Add ajax flag
    data['ajax'] = 'True';

    // Add segment comment if enabled
    if (typeof commentsSegEnabled !== 'undefined' && commentsSegEnabled) {
        var $commentBox = $row.find('.seg-comment-input');
        if ($commentBox.length) {
            data['comment'] = $commentBox.val() || '';
        }
    }

    // Validate segment comment if required
    if (typeof commentsSegRequired !== 'undefined' && commentsSegRequired) {
        if (!data['comment'] || !data['comment'].trim()) {
            if (typeof _show_error_box === 'function') {
                _show_error_box('Please provide a comment for this segment before submitting.', 4000);
            } else {
                alert('Please provide a comment for this segment before submitting.');
            }
            return $.Deferred().reject().promise();
        }
    }

    console.log('Submitting combined contrastive data:', data);

    // Show spinner
    var $statusIcon = $row.find('.status-indicator');
    var $button = $row.find('.button-submit-contrastive');
    $statusIcon.removeClass('glyphicon-ok').addClass('glyphicon-refresh').show();
    $button.prop('disabled', true);

    // Submit via AJAX
    return $.ajax({
        data: data,
        type: 'POST',
        url: form1.attr('action'),
        dataType: 'json',
        success: function(response) {
            console.log('Contrastive submission success:', response);

            if (response.saved) {
                // Hide status spinner
                $statusIcon.removeClass('glyphicon-refresh').addClass('glyphicon-ok').hide();

                // Update counters if they exist
                if (response.items_left_in_block !== undefined) {
                    $('#items-left-counter').text(response.items_left_in_block);
                }
                if (response.item_id !== undefined) {
                    $('#current-item-id').text(response.item_id);
                }

                // Mark row as completed
                $row.data('item-completed', 'True');
                $itemBox1.data('item-completed', 'True');
                $itemBox2.data('item-completed', 'True');
                $itemBox3.data('item-completed', 'True');

                // Update button text
                $button.text('Update').prop('disabled', false);

                // Check if all sentences are scored to enable document button
                if (typeof _all_sentences_scored === 'function' && _all_sentences_scored()) {
                    if (typeof _enable_document_box === 'function') {
                        _enable_document_box();
                    }
                    if (typeof prepopulateDocumentScoresFromSingleSentence === 'function') {
                        prepopulateDocumentScoresFromSingleSentence(data['score1'], data['score2'], data['score3']);
                    }
                }
            } else {
                // Show error
                $statusIcon.removeClass('glyphicon-refresh').hide();
                $button.prop('disabled', false);
                alert('Error saving scores: ' + (response.error_msg || 'Unknown error'));
            }
        },
        error: function(xhr, status, error) {
            console.error('Contrastive submission error:', error);
            $statusIcon.removeClass('glyphicon-refresh').hide();
            $button.prop('disabled', false);
            alert('An error occurred while submitting. Please try again.');
        }
    });
}

// Override submit_finish_document for contrastive mode
async function submit_finish_document_contrastive(override_tutorial_check) {
    override_tutorial_check = override_tutorial_check || false;

    // Validate document comment if required
    if (typeof commentsDocRequired !== 'undefined' && commentsDocRequired) {
        var $docComment = $('#doc-comment-input');
        if ($docComment.length && !$docComment.val().trim()) {
            if (typeof _show_error_box === 'function') {
                _show_error_box('Please provide a document comment before submitting.', 4000);
            } else {
                alert('Please provide a document comment before submitting.');
            }
            return false;
        }
    }

    // Get all contrastive rows
    var $rows = $('.contrastive-row');

    // Validate all forms if not skipping tutorial check
    if (!override_tutorial_check && typeof MQM_HANDLERS !== 'undefined') {
        var allValid = true;
        $rows.each(function() {
            var $row = $(this);
            var itemId = $row.data('item-id');

            for (var k = 1; k <= NUM_CANDIDATES; k++) {
                var $itemBox = $row.find('#item-' + itemId + '-' + k);
                var handler = MQM_HANDLERS[$itemBox.data('item-id')];
                if (handler && !handler.validate_form()) {
                    allValid = false;
                    return false;
                }
            }
            if (!allValid) return false;
        });

        if (!allValid) {
            return false;
        }
    }

    // Prevent multiclicks
    $("#button-next-doc").prop('disabled', true);

    $("#form-next-doc > input[name='end_timestamp']").val(Date.now() / 1000);

    // Submit each row
    try {
        for (var i = 0; i < $rows.length; i++) {
            var $row = $($rows[i]);
            var itemId = $row.data('item-id');
            var $itemBox1 = $row.find('#item-' + itemId + '-1');
            var $itemBox2 = $row.find('#item-' + itemId + '-2');
            var $itemBox3 = $row.find('#item-' + itemId + '-3');

            await submit_contrastive_row($row, $itemBox1, $itemBox2, $itemBox3);
        }

        // Add document comment to hidden form if enabled
        if (typeof commentsDocEnabled !== 'undefined' && commentsDocEnabled) {
            var $docComment = $('#doc-comment-input');
            if ($docComment.length) {
                var $commentInput = $("#form-next-doc").find('input[name="comment"]');
                if (!$commentInput.length) {
                    $('<input>').attr({type: 'hidden', name: 'comment', value: $docComment.val()}).appendTo('#form-next-doc');
                } else {
                    $commentInput.val($docComment.val());
                }
            }
        }
        $("#form-next-doc").trigger("submit");
    } catch (error) {
        console.error('Error submitting contrastive items:', error);
        await new Promise(function(resolve) { setTimeout(resolve, 5000); });
        $("#button-next-doc").prop('disabled', false);
    }
}

// Initialize when DOM is ready
$(document).ready(function() {
    // Check if toggle functionality should be enabled
    var enableToggle = typeof SKIP_DOC_SCORES !== 'undefined' && typeof SENTENCE_ITEM_COUNT !== 'undefined'
        ? (!SKIP_DOC_SCORES || SENTENCE_ITEM_COUNT > 1)
        : true;

    // Set up toggle functionality for source column clicks
    $('.contrastive-row').each(function() {
        var $row = $(this);
        var $hoverable = $row.find('.source-box-hoverable');

        if (enableToggle) {
            $hoverable.on('click', function(e) {
                // Don't toggle if clicking on interactive elements
                if ($(e.target).is('a, button, input, select, textarea, .error-span')) {
                    return;
                }

                var $row = $(this).closest('.contrastive-row');
                var $targetBox = $row.find('.target-box');
                var $toggleIcons = $row.find('.source-btn-toggle');

                if ($targetBox.is(':visible')) {
                    $targetBox.slideUp(200);
                    $toggleIcons.removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
                } else {
                    $targetBox.slideDown(200);
                    $toggleIcons.removeClass('glyphicon-menu-down').addClass('glyphicon-menu-up');
                }
            });
        } else {
            $hoverable.removeClass('source-box-hoverable');
            $hoverable.css('cursor', 'default');
        }
    });

    // Delay initialization to allow sliders to be created first
    setTimeout(function() {
        initializeContrastiveRows();
    }, 100);

    // Bind submit button for each contrastive row
    $('.button-submit-contrastive').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        var itemId = $(this).data('item-id');
        var $row = $(this).closest('.contrastive-row');
        var $itemBox1 = $row.find('#item-' + itemId + '-1');
        var $itemBox2 = $row.find('#item-' + itemId + '-2');
        var $itemBox3 = $row.find('#item-' + itemId + '-3');

        console.log('Submit button clicked for contrastive item:', itemId);

        // Validate all three translations have been scored
        var score1 = $itemBox1.find('input[name="score"]').val();
        var score2 = $itemBox2.find('input[name="score"]').val();
        var score3 = $itemBox3.find('input[name="score"]').val();

        console.log('Scores:', score1, score2, score3);

        var labels = ['A', 'B', 'C'];
        var scores = [score1, score2, score3];
        for (var i = 0; i < scores.length; i++) {
            var s = scores[i];
            if (s === '' || s === null || s === undefined || s == -1 || s === '-1') {
                _show_error_box('Please score all three translations before submitting.', 3000);
                return false;
            }
        }

        // Validate that low scores have error spans marked (ESA mode)
        var threshold = 75;
        var displayThreshold = 8;
        if (typeof scale100Enabled !== 'undefined' && scale100Enabled) {
            threshold = 80;
            displayThreshold = 80;
        }

        var itemBoxes = [$itemBox1, $itemBox2, $itemBox3];
        for (var j = 0; j < itemBoxes.length; j++) {
            var $box = itemBoxes[j];
            var numScore = parseFloat(scores[j]);
            var handler = (typeof MQM_HANDLERS !== 'undefined') ? MQM_HANDLERS[$box.data('item-id')] : null;

            if (handler && !isNaN(numScore) && numScore < threshold) {
                var mqmData = [];
                try {
                    mqmData = JSON.parse($box.find('input[name="mqm"]').val() || '[]');
                } catch(ex) {}

                var actualErrors = mqmData.filter(function(error) {
                    return error.severity !== 'neutral' && error.severity !== 'undecided';
                });

                if (actualErrors.length === 0) {
                    _show_error_box('Translation ' + labels[j] + ' has a score lower than ' + displayThreshold + ' but no error spans marked. Please mark errors before submitting.', 4000);
                    return false;
                }
            }
        }

        // Submit all three translations and handle row state
        submit_contrastive_row($row, $itemBox1, $itemBox2, $itemBox3).done(function(response) {
            console.log('Submit response:', response);
            if (response.saved) {
                // Show completion tick
                $row.find('.source-btn-done').show();

                // Show comment indicator if comment was provided
                var $commentBox = $row.find('.seg-comment-input');
                if ($commentBox.length && $commentBox.val().trim()) {
                    $row.find('.source-btn-comment').show();
                } else {
                    $row.find('.source-btn-comment').hide();
                }

                // Check if we should auto-advance
                var shouldAutoAdvance = typeof SKIP_DOC_SCORES !== 'undefined' && typeof SENTENCE_ITEM_COUNT !== 'undefined'
                    ? (!SKIP_DOC_SCORES || SENTENCE_ITEM_COUNT > 1)
                    : true;

                if (shouldAutoAdvance) {
                    // Hide current row sliders
                    $row.find('.target-box').slideUp(200);
                    $row.find('.source-btn-toggle')
                        .removeClass('glyphicon-menu-up')
                        .addClass('glyphicon-menu-down');

                    // Find next unannotated row and expand it
                    var $nextRow = $row.nextAll('.contrastive-row').filter(function() {
                        var $r = $(this);
                        var rid = $r.data('item-id');
                        var allDone = true;
                        for (var n = 1; n <= NUM_CANDIDATES; n++) {
                            var $b = $r.find('#item-' + rid + '-' + n);
                            var done = $b.data('item-completed') === 'True' || $b.data('item-completed') === true;
                            if (!done) { allDone = false; break; }
                        }
                        return !allDone;
                    }).first();

                    if ($nextRow.length > 0) {
                        $nextRow.find('.target-box').slideDown(200);
                        $nextRow.find('.source-btn-toggle')
                            .removeClass('glyphicon-menu-down')
                            .addClass('glyphicon-menu-up');

                        // Scroll to next row
                        $('html, body').animate({
                            scrollTop: $nextRow.offset().top - 100
                        }, 300);
                    }
                }
            }
        });
    });

    // Override the button-next-doc handler
    $("#button-next-doc").off("click");
    $("#button-next-doc").on("click", function() {
        submit_finish_document_contrastive(false);
    });

    // Sync document comment to hidden input on doc form submit
    $("#button-doc").on("click", function() {
        var $form = $(this).closest('form');

        // Set end_timestamp before submission
        $form.find('input[name="end_timestamp"]').val(Date.now() / 1000);

        if (typeof commentsDocEnabled !== 'undefined' && commentsDocEnabled) {
            var $docComment = $('#doc-comment-input');
            if ($docComment.length) {
                $form.find('input[name="comment"]').val($docComment.val() || '');
                if (typeof commentsDocRequired !== 'undefined' && commentsDocRequired && !$docComment.val().trim()) {
                    if (typeof _show_error_box === 'function') {
                        _show_error_box('Please provide a document comment before submitting.', 4000);
                    } else {
                        alert('Please provide a document comment before submitting.');
                    }
                    return false;
                }
            }
        }
    });

    // Override skip-tutorial if it exists
    $("#skip-tutorial").off("click");
    $("#skip-tutorial").on("click", function() {
        $("#skip-tutorial").prop('disabled', true);
        $(".button-submit-contrastive").trigger("click");
        $(".slider").slider('value', 0);
        submit_finish_document_contrastive(true);
    });
});

// Initialize row states after sliders are ready
function initializeContrastiveRows() {
    // Check if sliders should stay visible (single segment with skip_doc_scores)
    var keepSlidersVisible = typeof SKIP_DOC_SCORES !== 'undefined' && typeof SENTENCE_ITEM_COUNT !== 'undefined'
        && SKIP_DOC_SCORES && SENTENCE_ITEM_COUNT === 1;

    var first_unannotated_found = false;
    $('.contrastive-row').each(function() {
        var $row = $(this);
        var itemId = $row.data('item-id');
        var $button = $row.find('.button-submit-contrastive');
        var $targetBox = $row.find('.target-box');
        var $doneTick = $row.find('.source-btn-done');

        // Check if all translations have been scored
        var allCompleted = true;
        for (var k = 1; k <= NUM_CANDIDATES; k++) {
            var $box = $row.find('#item-' + itemId + '-' + k);
            var boxCompleted = $box.data('item-completed') === 'True' || $box.data('item-completed') === true;
            if (!boxCompleted) { allCompleted = false; break; }
        }

        if (allCompleted) {
            // Show tick icon
            $doneTick.show();
            $row.find('.status-indicator').hide();

            // Change button text to "Update"
            $button.text('Update');

            // Show comment indicator if comment exists
            var $commentBox = $row.find('.seg-comment-input');
            if ($commentBox.length && $commentBox.val().trim()) {
                $row.find('.source-btn-comment').show();
            }

            // Restore slider values from saved scores
            for (var m = 1; m <= NUM_CANDIDATES; m++) {
                var $itemBox = $row.find('#item-' + itemId + '-' + m);
                var score = $itemBox.data('item-score');
                if (score && score != -1 && score !== '-1') {
                    var $slider = $('#slider' + itemId + '-' + m);
                    if ($slider.length && typeof applyScoreToSliderElement === 'function') {
                        try {
                            applyScoreToSliderElement($slider, score);
                        } catch (e) {
                            console.error("Error applying score to slider" + m + ":", e);
                        }
                    }
                }
            }

            // Collapse or keep visible
            if (keepSlidersVisible) {
                $targetBox.addClass('active').show();
                $row.addClass('active');
                $row.find('.source-btn-toggle').removeClass('glyphicon-menu-down').addClass('glyphicon-menu-up');
            } else {
                $targetBox.hide();
                $row.find('.source-btn-toggle').removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
            }
        } else {
            // Hide tick icon
            $doneTick.hide();

            // First unannotated item should be expanded
            if (!first_unannotated_found || keepSlidersVisible) {
                first_unannotated_found = true;
                $targetBox.addClass('active').show();
                $row.addClass('active');
                $row.find('.source-btn-toggle')
                    .removeClass('glyphicon-menu-down')
                    .addClass('glyphicon-menu-up');
            } else {
                $targetBox.hide();
                $row.find('.source-btn-toggle').removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
            }
        }
    });
}

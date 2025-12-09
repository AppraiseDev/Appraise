/**
 * Pairwise ESA mode JavaScript
 * Handles pairwise submission with single button per row
 */

// Function to submit both translations in a pairwise row
function submit_pairwise_row($row, $itemBox1, $itemBox2) {
    // Set end timestamp for both
    var timestamp = Date.now() / 1000.0;
    $itemBox1.find('input[name="end_timestamp"]').val(timestamp);
    $itemBox2.find('input[name="end_timestamp"]').val(timestamp);
    
    // Get form data from both item-boxes
    var form1 = $itemBox1.find('form');
    var form2 = $itemBox2.find('form');
    
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
    
    // Add ajax flag
    data['ajax'] = 'True';
    
    console.log('Submitting combined pairwise data:', data);
    
    // Show spinner
    var $statusIcon = $row.find('.status-indicator');
    var $button = $row.find('.button-submit-pair');
    $statusIcon.removeClass('glyphicon-ok').addClass('glyphicon-refresh').show();
    $button.prop('disabled', true);
    
    // Submit via AJAX
    return $.ajax({
        data: data,
        type: 'POST',
        url: form1.attr('action'),
        dataType: 'json',
        success: function(response) {
            console.log('Pairwise submission success:', response);
            
            if (response.saved) {
                // Update status icon
                $statusIcon.removeClass('glyphicon-refresh').addClass('glyphicon-ok');
                
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
                
                // Update button text
                $button.text('Update').prop('disabled', false);
                
                // Check if all sentences are scored to enable document button
                if (typeof _all_sentences_scored === 'function' && _all_sentences_scored()) {
                    if (typeof _enable_document_box === 'function') {
                        _enable_document_box();
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
            console.error('Pairwise submission error:', error);
            $statusIcon.removeClass('glyphicon-refresh').hide();
            $button.prop('disabled', false);
            alert('An error occurred while submitting. Please try again.');
        }
    });
}

// Override submit_finish_document for pairwise mode
async function submit_finish_document_pairwise(override_tutorial_check=false) {
    // Get all pairwise rows
    var $rows = $('.pairwise-row');
    
    // Validate all forms if not skipping tutorial check
    if (!override_tutorial_check) {
        var allValid = true;
        $rows.each(function() {
            var $row = $(this);
            var itemId = $row.data('item-id');
            var $itemBox1 = $row.find('#item-' + itemId + '-1');
            var $itemBox2 = $row.find('#item-' + itemId + '-2');
            
            var handler1 = MQM_HANDLERS[$itemBox1.data('item-id')];
            var handler2 = MQM_HANDLERS[$itemBox2.data('item-id')];
            
            if (handler1 && !handler1.validate_form()) {
                allValid = false;
                return false;
            }
            if (handler2 && !handler2.validate_form()) {
                allValid = false;
                return false;
            }
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
            
            await submit_pairwise_row($row, $itemBox1, $itemBox2);
        }
        
        // Trigger hidden form if all is good
        $("#form-next-doc").trigger("submit");
    } catch (error) {
        console.error('Error submitting pairwise items:', error);
        // Re-enable next doc button in a few seconds if not
        await new Promise(resolve => setTimeout(resolve, 5_000));
        $("#button-next-doc").prop('disabled', false);
    }
}

// Toggle row visibility - show sliders and button
function _show_target_box() {
    var $hoverable = $(this);
    var $row = $hoverable.closest('.pairwise-row');
    var $targetBox = $row.find('.target-box');
    var $toggleIcons = $row.find('.source-btn-toggle');
    
    console.log("Showing target box for row");
    $targetBox.slideDown(200);
    $toggleIcons.removeClass('glyphicon-menu-down').addClass('glyphicon-menu-up');
}

// Toggle row visibility - hide sliders and button
function _hide_target_box() {
    var $hoverable = $(this);
    var $row = $hoverable.closest('.pairwise-row');
    var $targetBox = $row.find('.target-box');
    var $toggleIcons = $row.find('.source-btn-toggle');
    
    console.log("Hiding target box for row");
    $targetBox.slideUp(200);
    $toggleIcons.removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
}

// Initialize when DOM is ready
$(document).ready(function() {
    // IMPORTANT: Wait for MQM handlers to be initialized by direct-assessment-document-mqm-esa.js
    // This ensures error span functionality is available
    
    // Check if we should enable toggle functionality (disable if only 1 segment with skip_doc_scores)
    var enableToggle = typeof SKIP_DOC_SCORES !== 'undefined' && typeof SENTENCE_ITEM_COUNT !== 'undefined'
        ? (!SKIP_DOC_SCORES || SENTENCE_ITEM_COUNT > 1)
        : true;
    
    // Set up toggle functionality - bind click handler to source column that toggles row
    $('.pairwise-row').each(function() {
        var $row = $(this);
        var $hoverable = $row.find('.source-box-hoverable');
        
        // Only enable toggle if we have multiple segments or doc scores are not skipped
        if (enableToggle) {
            // Use simple click handler that toggles visibility
            $hoverable.on('click', function(e) {
                // Don't toggle if clicking on interactive elements
                if ($(e.target).is('a, button, input, select, textarea, .error-span')) {
                    return;
                }
                
                var $row = $(this).closest('.pairwise-row');
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
            // For single segment with skip_doc_scores, remove hoverable cursor
            $hoverable.removeClass('source-box-hoverable');
            $hoverable.css('cursor', 'default');
        }
    });
    
    // Delay initialization to allow sliders to be created first
    setTimeout(function() {
        initializePairwiseRows();
    }, 100);
    
    // Bind submit button for each pairwise row
    $('.button-submit-pair').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation(); // Prevent event bubbling
        
        var itemId = $(this).data('item-id');
        var $row = $(this).closest('.pairwise-row');
        var $itemBox1 = $row.find('#item-' + itemId + '-1');
        var $itemBox2 = $row.find('#item-' + itemId + '-2');
        
        console.log('Submit button clicked for pairwise item:', itemId);
        
        // Validate both translations have been scored
        var score1 = $itemBox1.find('input[name="score"]').val();
        var score2 = $itemBox2.find('input[name="score"]').val();
        
        console.log('Scores:', score1, score2);
        
        if (!score1 || score1 == -1 || score1 === '-1' || !score2 || score2 == -1 || score2 === '-1') {
            alert('Please score both translations before submitting.');
            return false;
        }
        
        // Validate that low scores have error spans marked
        var numScore1 = parseFloat(score1);
        var numScore2 = parseFloat(score2);
        
        // Get handlers to check if document-level (handler won't exist for document-level)
        var handler1 = MQM_HANDLERS[$itemBox1.data('item-id')];
        var handler2 = MQM_HANDLERS[$itemBox2.data('item-id')];
        
        // Only validate if handler exists (document-level items don't have handlers)
        if (handler1 && !isNaN(numScore1) && numScore1 < 75) {
            var mqm1Data = [];
            try {
                mqm1Data = JSON.parse($itemBox1.find('input[name="mqm"]').val() || '[]');
            } catch(e) {}
            
            var actualErrors1 = mqm1Data.filter(function(error) {
                return error.severity !== 'neutral' && error.severity !== 'undecided';
            });
            
            if (actualErrors1.length === 0) {
                alert('Translation A has a score lower than 8 but no error spans marked. Please mark errors before submitting.');
                return false;
            }
        }
        
        // Only validate if handler exists (document-level items don't have handlers)
        if (handler2 && !isNaN(numScore2) && numScore2 < 75) {
            var mqm2Data = [];
            try {
                mqm2Data = JSON.parse($itemBox2.find('input[name="mqm"]').val() || '[]');
            } catch(e) {}
            
            var actualErrors2 = mqm2Data.filter(function(error) {
                return error.severity !== 'neutral' && error.severity !== 'undecided';
            });
            
            if (actualErrors2.length === 0) {
                alert('Translation B has a score lower than 8 but no error spans marked. Please mark errors before submitting.');
                return false;
            }
        }
        
        // Submit both translations and handle row state after submission
        submit_pairwise_row($row, $itemBox1, $itemBox2).done(function(response) {
            console.log('Submit response:', response);
            if (response.saved) {
                // Show completion tick
                $row.find('.source-btn-done').show();
                
                // Check if we should auto-advance (skip if only 1 segment with skip_doc_scores)
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
                    var $nextRow = $row.nextAll('.pairwise-row').filter(function() {
                        var $r = $(this);
                        var itemId = $r.data('item-id');
                        var $box1 = $r.find('#item-' + itemId + '-1');
                        var $box2 = $r.find('#item-' + itemId + '-2');
                        var box1Completed = $box1.data('item-completed') === 'True' || $box1.data('item-completed') === true;
                        var box2Completed = $box2.data('item-completed') === 'True' || $box2.data('item-completed') === true;
                        return !(box1Completed && box2Completed);
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
                // If not auto-advancing (single segment with skip_doc_scores), keep sliders visible
            }
        });
    });
    
    // Override the button-next-doc handler
    $("#button-next-doc").off("click");
    $("#button-next-doc").on("click", function() {
        submit_finish_document_pairwise(false);
    });
    
    // Override skip-tutorial if it exists
    $("#skip-tutorial").off("click");
    $("#skip-tutorial").on("click", function() {
        $("#skip-tutorial").prop('disabled', true);
        $(".button-submit-pair").trigger("click");
        $(".slider").slider('value', 0);
        submit_finish_document_pairwise(true);
    });
});

// Separate function to initialize row states after sliders are ready
function initializePairwiseRows() {
    // Check if we should keep sliders visible (single segment with skip_doc_scores)
    var keepSlidersVisible = typeof SKIP_DOC_SCORES !== 'undefined' && typeof SENTENCE_ITEM_COUNT !== 'undefined'
        && SKIP_DOC_SCORES && SENTENCE_ITEM_COUNT === 1;
    
    // Initialize row states based on completion status
    var first_unannotated_found = false;
    $('.pairwise-row').each(function() {
        var $row = $(this);
        var itemId = $row.data('item-id');
        var isCompleted = $row.data('item-completed') === 'True' || $row.data('item-completed') === true;
        var $itemBox1 = $row.find('#item-' + itemId + '-1');
        var $itemBox2 = $row.find('#item-' + itemId + '-2');
        var $button = $row.find('.button-submit-pair');
        var $targetBox = $row.find('.target-box');
        var $doneTick = $row.find('.source-btn-done');
        
        // Check if both translations have been scored (item-boxes have completed status)
        var box1Completed = $itemBox1.data('item-completed') === 'True' || $itemBox1.data('item-completed') === true;
        var box2Completed = $itemBox2.data('item-completed') === 'True' || $itemBox2.data('item-completed') === true;
        var bothCompleted = box1Completed && box2Completed;
        
        if (bothCompleted) {
            // For completed items:
            // 1. Show tick icon
            $doneTick.show();
            
            // 2. Change button text to "Update"
            $button.text('Update');
            
            // 3. Restore slider values from saved scores
            var score1 = $itemBox1.data('item-score');
            var score2 = $itemBox2.data('item-score');
            
            if (score1 && score1 != -1 && score1 !== '-1') {
                var $slider1 = $('#slider' + itemId + '-1');
                if ($slider1.length && typeof applyScoreToSliderElement === 'function') {
                    try {
                        applyScoreToSliderElement($slider1, score1);
                    } catch (e) {
                        console.error("Error applying score to slider1:", e);
                    }
                }
            }
            if (score2 && score2 != -1 && score2 !== '-1') {
                var $slider2 = $('#slider' + itemId + '-2');
                if ($slider2.length && typeof applyScoreToSliderElement === 'function') {
                    try {
                        applyScoreToSliderElement($slider2, score2);
                    } catch (e) {
                        console.error("Error applying score to slider2:", e);
                    }
                }
            }
            
            // 4. Hide sliders by default (collapsed state) UNLESS it's a single segment with skip_doc_scores
            if (keepSlidersVisible) {
                // Keep sliders visible for single segment
                $targetBox.addClass('active').show();
                $row.addClass('active');
                $row.find('.source-btn-toggle').removeClass('glyphicon-menu-down').addClass('glyphicon-menu-up');
            } else {
                // Hide sliders normally
                $targetBox.hide();
                $row.find('.source-btn-toggle').removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
            }
        } else {
            // For uncompleted items:
            // Hide tick icon
            $doneTick.hide();
            
            // First unannotated item should be expanded (or if single segment with skip_doc_scores, always expanded)
            if (!first_unannotated_found || keepSlidersVisible) {
                first_unannotated_found = true;
                $targetBox.addClass('active').show();
                $row.addClass('active');
                $row.find('.source-btn-toggle')
                    .removeClass('glyphicon-menu-down')
                    .addClass('glyphicon-menu-up');
            } else {
                // Hide all other unannotated items
                $targetBox.hide();
                $row.find('.source-btn-toggle').removeClass('glyphicon-menu-up').addClass('glyphicon-menu-down');
            }
        }
    });
}

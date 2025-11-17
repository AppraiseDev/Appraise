// constants and utils
// Global flag to control tracking underline feature
var TRACKING_ENABLED = true;

const SEVERITY_TO_COLOR = {
    "critical": "#f33c",
    "major": "#c44a",
    "minor": "#fbba",
    "neutral": "#f993",
    "undecided": "#99d9",
}
const SEVERITY_TO_SCORE = {
    "major": 5,
    "minor": 1,
    "neutral": 0,
    "critical": Number.NaN,
    "undecided": Number.NaN,
}
const SEVERITY_TO_NEXT = {
    "neutral": "minor",
    "undecided": "minor",
    "minor": "major",
    "major": "undecided",
    "critical": "undecided",
}
const ERROR_TYPES = {
    "Terminology": {
        "Inconsistent with terminology resource": {},
        "Inconsistent use of terminology": {},
        "Wrong term": {},
    },
    "Accuracy": {
        "Mistranslation": {},
        "Overtranslation": {},
        "Undertranslation": {},
        "Addition": {},
        "Omission": {},
        "Do not translate": {},
        "Untranslated": {},
    },
    "Linguistic conventions": {
        "Grammar": {},
        "Punctuation": {},
        "Spelling": {},
        "Unintelligible": {},
        "Character encoding": {},
        "Textual conventions": {},
    },
    "Style": {
        "Organization style": {},
        "Third-party style": {},
        "Inconsistent with external reference": {},
        "Language register": {},
        "Awkward style": {},
        "Unidiomatic style": {},
        "Inconsistent style": {},
    },
    "Locale convention": {
        "Number format": {},
        "Currency format": {},
        "Measurement format": {},
        "Time format": {},
        "Date format": {},
        "Address format": {},
        "Telephone format": {},
        "Shortcut key": {},
    },
    "Audience appropriateness": {
        "Culture-specific reference": {},
        "Offensive": {},
    },
    "Design and markup": {
        "Layout": {},
        "Markup tag": {},
        "Truncation/text espansion": {},
        "Missing text": {},
        "Link/cross-reference": {},
    },
    "Other": {},
}


Object.keys(SEVERITY_TO_COLOR).map((key) => {
    $(`#instruction_sev_${key}`).css("background-color", SEVERITY_TO_COLOR[key])
})
// https://stackoverflow.com/questions/4817029/whats-the-best-way-to-detect-a-touch-screen-device-using-javascript
const IS_MOBILE = (('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (navigator.msMaxTouchPoints > 0) || window.matchMedia("(any-pointer: coarse)").matches);

function waitout_js_loop() {
    return new Promise(resolve => setTimeout(resolve, 1))
}

String.prototype.capitalize = function () {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

var MQM_HANDLERS = {}
var MQM_TYPE;

async function get_error_type() {
    // ESA doesn't have error types
    if (MQM_TYPE == "ESA") {
        return null
    }
    let error_stack = []
    let possible_errors = ERROR_TYPES

    while (Object.keys(possible_errors).length != 0) {
        let el_dialog = $("#error-type-form")

        el_dialog.text(error_stack.join(" > ") + " > ____")
        let result = await new Promise(function (resolve, reject) {
            el_dialog.dialog({
                autoOpen: true,
                width: 350,
                modal: true,
                title: "Please select error type",
                // closing is permitted but will yield null
                close: () => resolve(null),
                buttons: Object.fromEntries(
                    Object.keys(possible_errors).map(x => [x, () => { resolve(x); el_dialog.dialog("close") }])
                )
            })
        })
        if (result == null) {
            return null
        }
        error_stack.push(result)
        possible_errors = possible_errors[result]
    }

    return error_stack
}

$(document).ready(() => {
    MQM_TYPE = JSON.parse($('#mqm-type-payload').html())

    // sliders are present only for ESA
    if (MQM_TYPE != "ESA") {
        $(".esa_slider").toggle(false)
    }

    // bind UI events
    // TODO: this does not work very well because of ???
    $('.button-reset').on("click", (event) => {
        if (confirm("Do you really want to reset the segment annotations?")) {
            MQM_HANDLERS[$(event.target).parents('.item-box').attr("data-item-id")].reset()
        }
    });

    // hide next doc button for now
    toggle_doc_button(false)
    $("#button-next-doc").on("click", () => submit_finish_document(false))

    $(".item-box").each((_i, el) => {
        let $el = $(el);
        
        // Skip document-level items (those with document-box class)
        if ($el.find('.document-box').length > 0) {
            console.log("Skipping MQM handler for document-level item:", $el.attr("data-item-id"));
            return;
        }
        
        MQM_HANDLERS[$el.attr("data-item-id")] = new MQMItemHandler(el)
    })

    $("#form-next-doc > input[name='start_timestamp']").val(Date.now() / 1000)

    // highlight instructions
    Object.keys(SEVERITY_TO_COLOR).map((key) => {
        $(`#instruction_sev_${key}`).css("background-color", SEVERITY_TO_COLOR[key])
    })

    $("#skip-tutorial").on("click", () => {
        // prevent multiclick
        $("#skip-tutorial").prop('disabled', true);

        $(".button-submit").trigger("click");
        $(".slider").slider('value', 0);
        submit_finish_document(override_tutorial_check=true)
    })

    $("#form-next-doc > input[name='start_timestamp']").val(Date.now() / 1000)

    // show submit button only on MQM and not ESA
    $(".button-submit").toggle(MQM_TYPE == "MQM")

    let instructions_show = localStorage.getItem("appraise-instructions-show")
    if (instructions_show == null) instructions_show = true;
    else instructions_show = instructions_show == "true";

    $("#instructions-show").on("click", () => {
        instructions_show = !instructions_show;
        $("#instructions-show").text(instructions_show ? "Hide instructions" : "Show instructions")
        localStorage.setItem("appraise-instructions-show", instructions_show);
        $("#instructions").toggle(instructions_show)
    })

    // will be overriden
    instructions_show = !instructions_show
    $("#instructions-show").trigger("click")
});

function _all_sentences_scored() {
    let items_left = $('.item-box').filter((_i, el) => $(el).attr('data-item-completed') == "False").length;
    return items_left == 0;
}

function _change_item_status_icon(item_box, icon_name) {
    let icon_box = item_box.find('.status-indicator').removeClass('glyphicon-refresh glyphicon-ok glyphicon-flag');
    icon_box.addClass(`glyphicon-${icon_name}`)
}


function submit_form_ajax(item_box) {
    let promise = $.ajax({
        data: item_box.find('form').serialize(),
        type: 'POST',
        // post to the same url it was loaded from
        url: '',
        dataType: 'json',
        beforeSend: function () {
            console.log('Sending AJAX request, item-id=', item_box.data('item-id'));
            _change_item_status_icon(item_box, 'refresh');
        },
        success: function (data) {
            console.log(`Success, saved=${data.saved} next_item=${data.item_id}`);
            if (data.saved) {
                _change_item_status_icon(item_box, 'ok');

            } else {
                _change_item_status_icon(item_box, 'warning-sign');
                _show_error_box(data.error_msg, 10_000);
            }
        },
        error: function (x, s, t) {
            console.log('Error:', x, s, t);
            _change_item_status_icon(item_box, 'warning-sign');
            _show_error_box(
                'An unrecognized error has occured. ' +
                'Please reload the page or try again in a moment. ',
                5_000
            );
        },
    });

    return promise
}

async function submit_finish_document(override_tutorial_check=false) {
    // make sure to bail if there's some tutorial issues
    if (!override_tutorial_check) {
        for (let el of $(".item-box")) {
            if (!MQM_HANDLERS[$(el).attr("data-item-id")].validate_form()) {
                return false
            }
        }
    }
    // prevent multiclicks
    $("#button-next-doc").prop('disabled', true);

    $("#form-next-doc > input[name='end_timestamp']").val(Date.now() / 1000)

    // wait for individual items to be submitted
    try {
        for (const el of $(".item-box")) {
            await submit_form_ajax($(el))
        }

        // trigger hidden form if all is good
        $("#form-next-doc").trigger("submit")
    } catch {
        // re-enable next doc button in a few seconds if not
        await new Promise(resolve => setTimeout(resolve, 5_000))
        $("#button-next-doc").prop('disabled', false);
    }
}
function decodeEntities(html) {
    var txt = document.createElement("textarea");
    txt.innerHTML = html;
    return txt.value;
}

function _show_error_box(text, timeout = 2000) {
    let obj = $(`<div class="alert_message" style="display: none">${text}</div>`)
    $("body").append(obj);
    obj.fadeIn(200);
    // disappear in 2s
    setTimeout(() => { obj.fadeOut(700, () => { obj.remove() }) }, timeout);
}

function fuzzy_abs_match(a, b, tol) {
    return a == b || Math.abs(a - b) <= tol
}

function toggle_doc_button(visible) {
    $("#button-next-doc").toggle(visible)
    // Keep the fake button always hidden
    // $("#button-next-doc-fake").toggle(!visible)
}

/**
 * Extract diff information from HTML text containing <span class="diff diff-xxx"> tags
 * Returns an object with:
 *   - plainText: the text content without HTML tags
 *   - diffMap: array mapping character index to diff class (diff-sub, diff-ins, diff-del)
 */
function extractDiffInfo(htmlText) {
    console.log('DEBUG extractDiffInfo: input HTML length:', htmlText.length);
    console.log('DEBUG extractDiffInfo: first 500 chars:', htmlText.substring(0, 500));
    
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlText;
    const diffMap = []; // Array mapping char index to diff class
    let plainText = ''; // Plain text without HTML tags
    
    // Check if any diff spans exist
    const diffSpans = tempDiv.querySelectorAll('.diff');
    console.log('DEBUG extractDiffInfo: found', diffSpans.length, 'diff spans in input HTML');
    if (diffSpans.length > 0) {
        console.log('DEBUG extractDiffInfo: first diff span classes:', diffSpans[0].className);
    }
    
    let charIndex = 0;
    function traverse(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent;
            // Check if this text node is inside a diff span
            let currentParent = node.parentElement;
            let diffClass = null;
            
            while (currentParent && currentParent !== tempDiv) {
                if (currentParent.classList && currentParent.classList.contains('diff')) {
                    // Find the specific diff class (diff-sub, diff-ins, or diff-del)
                    for (const cls of currentParent.classList) {
                        if (cls.startsWith('diff-')) {
                            diffClass = cls;
                            break;
                        }
                    }
                    break;
                }
                currentParent = currentParent.parentElement;
            }
            
            // Map each character to its diff class and build plain text
            for (let i = 0; i < text.length; i++) {
                diffMap[charIndex++] = diffClass;
                plainText += text[i];
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'BR') {
                diffMap[charIndex] = 'br'; // Mark BR positions
                plainText += '\n'; // Use newline for BR in plain text
                charIndex++;
            } else {
                for (const child of node.childNodes) {
                    traverse(child);
                }
            }
        }
    }
    
    traverse(tempDiv);
    
    console.log('DEBUG extractDiffInfo: plainText length:', plainText.length);
    console.log('DEBUG extractDiffInfo: plainText first 200 chars:', plainText.substring(0, 200));
    console.log('DEBUG extractDiffInfo: diffMap entries with diff classes:', diffMap.filter(c => c && c.startsWith('diff-')).length);
    
    return { plainText, diffMap };
}

class MQMItemHandler {
    constructor(el) {
        this.el = $(el)
        this.initialize()
    }

    async initialize() {
        this.el_source = this.el.find(".source-text")
        this.el_target = this.el.find(".target-text")
        this.el_slider = this.el.find('.slider')
        // for Appraise reasons it's a JSON string encoding JSON
        this.mqm = JSON.parse(JSON.parse(this.el.children('#mqm-payload').html()))

        if (!Array.isArray(this.mqm)) {
            this.tutorial = this.mqm["tutorial"]
            this.mqm = this.mqm["payload"]

            this.el.find(".tutorial-text").html("<b>TUTORIAL:</b> " + this.tutorial["instruction"])

            // unhide multiple times but doesn't matter
            $("#tutorial-text").toggle(true)
        } else {
            this.tutorial = false
        }
        this.mqm_submitted = structuredClone(this.mqm)
        this.mqm_orig = JSON.parse(JSON.parse(this.el.children('#mqm-payload-orig').html()))
        
        let _src_raw = JSON.parse(this.el.children('#text-source-payload').html()).trim()
        this.text_source_orig = decodeEntities(_src_raw)
        this.source_is_multimodal = (
            _src_raw.startsWith("<video") ||
            _src_raw.startsWith("<audio") ||
            _src_raw.startsWith("<img")
        )
        // Detect contrastive ESA or pairwise ESA mode
        this.pairwise_esa = ($(".pairwise-row").length > 0)
        this.contrastive_esa = ($("#shared-source-text-content").length > 0) || this.pairwise_esa
        // NOTE: we don't decode entities for the target text, which might cause false positive annotated errors
        this.text_target_orig = JSON.parse(this.el.children('#text-target-payload').html()).trim()
        
        this.SELECTION_STATE = []
        this.HOVER_UNDECIDED_SPANS = new Set()
        this.LAST_MOUSE_TIMESTAMP = 0
        this.MQM_DELETE_TIMER = null

        this.el_slider.slider({
            orientation: "horizontal", range: "min", change: (event) => {
                // update score in the form
                this.el.find("input[name='score']").val(this.el_slider.slider('value'))

                // if this was triggered by human then mark it as unsaved
                if (event.originalEvent) {
                    this.update_item_times()
                    this.note_change(true)
                }
            }
        })
        let score = parseFloat(this.el.children('#score-payload').html())

    
        // Extract diff information from the HTML before processing
        // This preserves the <span class="diff diff-xxx"> markup for pairwise comparisons
        // and returns the plain text without HTML tags
        let diffInfo = extractDiffInfo(this.text_target_orig);
        let diffMap = diffInfo.diffMap;
        let plainText = diffInfo.plainText;
        
        console.log('DEBUG: text_target_orig:', this.text_target_orig.substring(0, 200));
        console.log('DEBUG: plainText:', plainText.substring(0, 200));
        console.log('DEBUG: diffMap sample:', diffMap.slice(0, 50));
        console.log('DEBUG: diffMap has diff classes:', diffMap.some(c => c && c.startsWith('diff-')));
        
        // Use the plain text for rendering (without HTML tags)
        let textToRender = plainText;
        
        // setup_span_structure
        // First, handle <br/> and <br> tags by splitting the text and processing each segment
        // Note: plainText uses \n for line breaks
        let segments = textToRender.split(/(\n)/g);
        let char_index = 0;
        let html_target = segments.map((segment) => {
            // If this is a newline, convert to br tag
            if (segment === '\n') {
                // Skip the BR in the diffMap
                if (diffMap[char_index] === 'br') {
                    char_index++;
                }
                return '<br>';
            }
            // Otherwise, split into characters and wrap in spans
            return segment.split("").map((v) => {
                // Get diff class for this character position
                let diffClass = diffMap[char_index] || null;
                let diffClassAttr = diffClass ? ` diff ${diffClass}` : '';
                
                if (char_index < 10 && diffClass) {
                    console.log(`DEBUG char ${char_index}: "${v}" has diffClass: ${diffClass}`);
                }
                
                let span = `<span class="mqm_char${diffClassAttr}" id="target_char_${char_index}" char_id="${char_index}">${v}</span>`;
                char_index++;
                return span;
            }).join("");
        }).join("") + " <span class='mqm_char span_missing' id='target_char_missing' char_id='missing'>[MISSING]</span>"
        // Store the actual character count (excluding br tags)
        this.text_target_char_count = char_index;
        this.el_target.html(html_target)
        
        // Debug: Check if diff classes are present in rendered HTML
        let diffSpans = this.el_target.find('.mqm_char.diff-sub, .mqm_char.diff-ins, .mqm_char.diff-del');
        console.log(`DEBUG: Found ${diffSpans.length} spans with diff classes after rendering`);
        if (diffSpans.length > 0) {
            console.log('DEBUG: First diff span:', diffSpans.first()[0]);
            console.log('DEBUG: First diff span classes:', diffSpans.first().attr('class'));
        }

        this.redraw_mqm()

        // call setup only once
        this.setup_span_click_handlers()

        // set fake MQM value
        if (MQM_TYPE == "MQM") {
            this.el_slider.slider('value', 0);   
        }
        // set previous value
        if (score != -1) {
            this.el_slider.slider('value', score);
        }

        // handle character alignment estimation
        if (!this.source_is_multimodal) {

            // Check if we're in contrastive mode with shared source text
            let $sharedSource = $("#shared-source-text-content");
            if (this.contrastive_esa) {
                let len_src;
                
                // For pairwise mode, wrap the source text in each pairwise row
                if (this.pairwise_esa) {
                    let $pairwiseRow = this.el.closest(".pairwise-row");
                    let $rowSourceDisplay = $pairwiseRow.find(".source-text-display");
                    
                    // Initialize source text for this row only once
                    if (!$rowSourceDisplay.children(".mqm_char_src").length) {
                        let src_segments = this.text_source_orig.split(/(<br\s*\/?>)/gi);
                        let src_char_index = 0;
                        let html_source = src_segments.map((segment) => {
                            if (segment.match(/^<br\s*\/?>$/i)) {
                                return segment;
                            }
                            return segment.split("").map((v) => {
                                if (v == "\n") {
                                    return "<br>"
                                }
                                let span = `<span class="mqm_char_src" char_id="${src_char_index}">${v}</span>`;
                                src_char_index++;
                                return span;
                            }).join("");
                        }).join("")
                        $rowSourceDisplay.html(html_source)
                        $rowSourceDisplay.attr("data-char-count", src_char_index)
                        len_src = src_char_index;
                    } else {
                        len_src = parseInt($rowSourceDisplay.attr("data-char-count"))
                    }
                } else {
                    // Original contrastive mode: Initialize shared source text only once
                    if (!$sharedSource.children(".mqm_char_src").length) {
                        // Handle <br/> tags in source text like we do for target
                        let src_segments = this.text_source_orig.split(/(<br\s*\/?>)/gi);
                        let src_char_index = 0;
                        let html_source = src_segments.map((segment) => {
                            // If this is a br tag, preserve it as-is
                            if (segment.match(/^<br\s*\/?>$/i)) {
                                return segment;
                            }
                            // Otherwise, split into characters and wrap in spans
                            return segment.split("").map((v) => {
                                if (v == "\n") {
                                    return "<br>" // preserve newlines
                                }
                                let span = `<span class="mqm_char_src" id="source_char_${src_char_index}" char_id="${src_char_index}">${v}</span>`;
                                src_char_index++;
                                return span;
                            }).join("");
                        }).join("")
                        $sharedSource.html(html_source)
                        // Store the character count on the element for reuse
                        $sharedSource.attr("data-char-count", src_char_index)
                        len_src = src_char_index;
                    } else {
                        // Use stored character count
                        len_src = parseInt($sharedSource.attr("data-char-count"))
                    }
                }
                
                await waitout_js_loop()

                let len_tgt = this.text_target_char_count;
                
                // Collect all other target texts for cross-highlighting
                let other_targets = [];
                $(".item-box").each((idx, other_el) => {
                    let $other_el = $(other_el);
                    // Skip if this is the current item
                    if ($other_el.attr("data-item-id") === this.el.attr("data-item-id")) {
                        return;
                    }
                    let $other_target = $other_el.find(".target-text");
                    if ($other_target.length > 0) {
                        let other_char_count = $other_target.children(".mqm_char").not(".span_missing").length;
                        other_targets.push({
                            element: $other_target,
                            char_count: other_char_count
                        });
                    }
                });
                
                // Wire up target chars to highlight shared source and other targets
                if (this.pairwise_esa) {
                    // For pairwise mode: highlight only within the same pairwise row
                    let $pairwiseRow = this.el.closest(".pairwise-row");
                    let $rowSource = $pairwiseRow.find(".source-text-display .mqm_char_src");
                    let row_len_src = $rowSource.length;
                    
                    // Find the other target in the same row
                    let $otherItemBox = $pairwiseRow.find(".item-box").not(this.el);
                    let $otherTarget = $otherItemBox.find(".target-text .mqm_char").not(".span_missing");
                    let other_len_tgt = $otherTarget.length;
                    
                    this.el_target.children(".mqm_char").each((i, el) => {
                        $(el).on("mouseenter", () => {
                            if (!TRACKING_ENABLED) return;
                            
                            let tgt_char_i = Number.parseInt($(el).attr("char_id"))
                            let src_char_i = Math.floor(tgt_char_i * row_len_src / len_tgt)
                            
                            // Clear all underlines first
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqq_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                            
                            let highlight_width = Math.floor(16 / 2)
                            
                            // Highlight corresponding position in row source (gray)
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, src_char_i - range); i <= Math.min(row_len_src - 1, src_char_i + range); i++) {
                                    $rowSource.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight this target character itself
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, tgt_char_i - range); i <= Math.min(len_tgt - 1, tgt_char_i + range); i++) {
                                    this.el_target.children(`.mqm_char[char_id="${i}"]`).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight corresponding position in other target within same row
                            if ($otherTarget.length > 0) {
                                let other_char_i = Math.floor(tgt_char_i * other_len_tgt / len_tgt)
                                
                                for (let range = highlight_width; range > 0; range--) {
                                    let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                    for (let i = Math.max(0, other_char_i - range); i <= Math.min(other_len_tgt - 1, other_char_i + range); i++) {
                                        $otherTarget.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                    }
                                }
                            }
                        })
                        
                        $(el).on("mouseleave", () => {
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                        })
                    })
                    
                    // Add hover handlers for source text
                    $rowSource.each((i, el) => {
                        $(el).on("mouseenter", () => {
                            if (!TRACKING_ENABLED) return;
                            
                            let src_char_i = Number.parseInt($(el).attr("char_id"))
                            
                            // Clear all underlines first
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                            
                            let highlight_width = Math.floor(16 / 2)
                            
                            // Highlight source character itself
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, src_char_i - range); i <= Math.min(row_len_src - 1, src_char_i + range); i++) {
                                    $rowSource.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight corresponding position in this target
                            let tgt_char_i = Math.floor(src_char_i * len_tgt / row_len_src)
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, tgt_char_i - range); i <= Math.min(len_tgt - 1, tgt_char_i + range); i++) {
                                    this.el_target.children(`.mqm_char[char_id="${i}"]`).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight corresponding position in other target
                            if ($otherTarget.length > 0) {
                                let other_char_i = Math.floor(src_char_i * other_len_tgt / row_len_src)
                                for (let range = highlight_width; range > 0; range--) {
                                    let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                    for (let i = Math.max(0, other_char_i - range); i <= Math.min(other_len_tgt - 1, other_char_i + range); i++) {
                                        $otherTarget.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                    }
                                }
                            }
                        })
                        
                        $(el).on("mouseleave", () => {
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                        })
                    })
                } else {
                    // Original contrastive mode: highlight across all items
                    this.el_target.children(".mqm_char").each((i, el) => {
                        // on hover
                        $(el).on("mouseenter", () => {
                            if (!TRACKING_ENABLED) return;
                            
                            // get char position from attribute
                            let tgt_char_i = Number.parseInt($(el).attr("char_id"))
                            // approximate position in source
                            let src_char_i = Math.floor(tgt_char_i * len_src / len_tgt)
                            // remove underline from all mqm
                            $sharedSource.children(".mqm_char_src").css("text-decoration", "")

                            let highlight_width = Math.floor(16 / 2)
                            // set underline to the corresponding character and its neighbours in source (green tones)
                            for (let range = highlight_width; range > 0; range--) {
                                // extrapolate range between #161 and #5d5 (green tones)
                                let color_r = (Math.floor((range-1)/highlight_width * (0x5 - 0x1))+0x1).toString(16)
                                let color_g = (Math.floor((range-1)/highlight_width * (0xd - 0x6))+0x6).toString(16)
                                let color_b = (Math.floor((range-1)/highlight_width * (0x5 - 0x1))+0x1).toString(16)
                                for (let i = Math.max(0, src_char_i - range); i <= Math.min(len_src, src_char_i + range); i++) {
                                    $sharedSource.children(`#source_char_${i}`).css("text-decoration", `underline 20% #${color_r}${color_g}${color_b} solid`)
                                }
                            }
                            
                            // Highlight corresponding positions in other target texts
                            other_targets.forEach((other_target) => {
                                let other_char_i = Math.floor(tgt_char_i * other_target.char_count / len_tgt)
                                // Remove previous highlighting from other target
                                other_target.element.children(".mqm_char").css("text-decoration", "")
                                
                                // Apply graduated underline to other target (green tones)
                                for (let range = highlight_width; range > 0; range--) {
                                    // extrapolate range between #161 and #5d5 (green tones)
                                    let color_r = (Math.floor((range-1)/highlight_width * (0x5 - 0x1))+0x1).toString(16)
                                    let color_g = (Math.floor((range-1)/highlight_width * (0xd - 0x6))+0x6).toString(16)
                                    let color_b = (Math.floor((range-1)/highlight_width * (0x5 - 0x1))+0x1).toString(16)
                                    for (let i = Math.max(0, other_char_i - range); i <= Math.min(other_target.char_count - 1, other_char_i + range); i++) {
                                        other_target.element.children(`.mqm_char[char_id="${i}"]`).css("text-decoration", `underline 15% #${color_r}${color_g}${color_b} solid`)
                                    }
                                }
                            });
                        })
                        // on leave remove all decorations
                        $(el).on("mouseleave", () => {
                            $sharedSource.children(".mqm_char_src").css("text-decoration", "")
                            // Remove decorations from all other targets
                            other_targets.forEach((other_target) => {
                                other_target.element.children(".mqm_char").css("text-decoration", "")
                            });
                        })
                    })
                }
            } else {
                // Original non-contrastive mode: use local source text
                // Handle <br/> tags in source text
                let src_segments = this.text_source_orig.split(/(<br\s*\/?>)/gi);
                let src_char_index = 0;
                let html_source = src_segments.map((segment) => {
                    // If this is a br tag, preserve it as-is
                    if (segment.match(/^<br\s*\/?>$/i)) {
                        return segment;
                    }
                    // Otherwise, split into characters and wrap in spans
                    return segment.split("").map((v) => {
                        if (v == "\n") {
                            return "<br>" // preserve newlines
                        }
                        let span = `<span class="mqm_char_src" id="source_char_${src_char_index}" char_id="${src_char_index}">${v}</span>`;
                        src_char_index++;
                        return span;
                    }).join("");
                }).join("")
                this.el_source.html(html_source)

                await waitout_js_loop()

                let len_src = src_char_index;
                let len_tgt = this.text_target_char_count;
                
                if (this.pairwise_esa) {
                    // For pairwise mode: highlight only within the same pairwise row
                    let $pairwiseRow = this.el.closest(".pairwise-row");
                    let $rowSource = $pairwiseRow.find(".source-text-display .mqm_char_src");
                    let row_len_src = $rowSource.length;
                    
                    // Find the other target in the same row
                    let $otherItemBox = $pairwiseRow.find(".item-box").not(this.el);
                    let $otherTarget = $otherItemBox.find(".target-text .mqm_char").not(".span_missing");
                    let other_len_tgt = $otherTarget.length;
                    
                    this.el_target.children(".mqm_char").each((i, el) => {
                        $(el).on("mouseenter", () => {
                            if (!TRACKING_ENABLED) return;
                            
                            let tgt_char_i = Number.parseInt($(el).attr("char_id"))
                            let src_char_i = Math.floor(tgt_char_i * row_len_src / len_tgt)
                            
                            // Clear all underlines first
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                            
                            let highlight_width = Math.floor(16 / 2)
                            
                            // Highlight corresponding position in row source
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, src_char_i - range); i <= Math.min(row_len_src - 1, src_char_i + range); i++) {
                                    $rowSource.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight this target character itself
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, tgt_char_i - range); i <= Math.min(len_tgt - 1, tgt_char_i + range); i++) {
                                    this.el_target.children(`.mqm_char[char_id="${i}"]`).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight corresponding position in other target within same row
                            if ($otherTarget.length > 0) {
                                let other_char_i = Math.floor(tgt_char_i * other_len_tgt / len_tgt)
                                
                                for (let range = highlight_width; range > 0; range--) {
                                    let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                    for (let i = Math.max(0, other_char_i - range); i <= Math.min(other_len_tgt - 1, other_char_i + range); i++) {
                                        $otherTarget.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                    }
                                }
                            }
                        })
                        
                        $(el).on("mouseleave", () => {
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                        })
                    })
                    
                    // Add hover handlers for source text
                    $rowSource.each((i, el) => {
                        $(el).on("mouseenter", () => {
                            if (!TRACKING_ENABLED) return;
                            
                            let src_char_i = Number.parseInt($(el).attr("char_id"))
                            
                            // Clear all underlines first
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                            
                            let highlight_width = Math.floor(16 / 2)
                            
                            // Highlight source character itself
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, src_char_i - range); i <= Math.min(row_len_src - 1, src_char_i + range); i++) {
                                    $rowSource.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight corresponding position in this target
                            let tgt_char_i = Math.floor(src_char_i * len_tgt / row_len_src)
                            for (let range = highlight_width; range > 0; range--) {
                                let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                for (let i = Math.max(0, tgt_char_i - range); i <= Math.min(len_tgt - 1, tgt_char_i + range); i++) {
                                    this.el_target.children(`.mqm_char[char_id="${i}"]`).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                }
                            }
                            
                            // Highlight corresponding position in other target
                            if ($otherTarget.length > 0) {
                                let other_char_i = Math.floor(src_char_i * other_len_tgt / row_len_src)
                                for (let range = highlight_width; range > 0; range--) {
                                    let color = (Math.floor((range-1)/highlight_width * (0xb - 0x7))+0x7).toString(16)
                                    for (let i = Math.max(0, other_char_i - range); i <= Math.min(other_len_tgt - 1, other_char_i + range); i++) {
                                        $otherTarget.eq(i).css("text-decoration", `underline 10% #${color}${color}${color} solid`)
                                    }
                                }
                            }
                        })
                        
                        $(el).on("mouseleave", () => {
                            $rowSource.css("text-decoration", "")
                            this.el_target.children(".mqm_char").css("text-decoration", "")
                            if ($otherTarget.length > 0) {
                                $otherTarget.css("text-decoration", "")
                            }
                        })
                    })
                } else {
                    // Original non-pairwise mode
                    this.el_target.children(".mqm_char").each((i, el) => {
                        // on hover
                        $(el).on("mouseenter", () => {
                            // get char position from attribute
                            let tgt_char_i = Number.parseInt($(el).attr("char_id"))
                            // approximate position
                            let src_char_i = Math.floor(tgt_char_i * len_src / len_tgt)
                            // remove underline from all mqm
                            this.el_source.children(".mqm_char_src").css("text-decoration", "")

                            let highlight_width = Math.floor(16 / 2)
                            // set underline to the corresponding character and its neighbours
                            for (let range = highlight_width; range > 0; range--) {
                                // extrapolate range between #111 and #ddd
                                let color = (Math.floor((range-1)/highlight_width * (0xd - 0x1))+0x1).toString(16)
                                for (let i = Math.max(0, src_char_i - range); i <= Math.min(len_src, src_char_i + range); i++) {
                                    this.el_source.children(`#source_char_${i}`).css("text-decoration", `underline 15% #${color}${color}${color} solid`)
                                }
                            }
                        })
                        // on leave remove all decorations
                        $(el).on("mouseleave", () => {
                            this.el_source.children(".mqm_char_src").css("text-decoration", "")
                        })
                    })
                }
            }
        }


        // slider bubble handling
        if (this.contrastive_esa) {
            this.el_slider.find(".ui-slider-handle").append("<div class='slider-bubble'>10</div>")
        } else {
            this.el_slider.find(".ui-slider-handle").append("<div class='slider-bubble'>100</div>")
        }
        let refresh_bubble = () => {
            var value = this.el_slider.slider('value')
            // Divide by 10 and get ceiled value
            if (this.contrastive_esa) {
                value = Math.min(10, Math.ceil((value + 0.1) / 10));
            }
            this.el_slider.find(".slider-bubble").text(value)
        }
        this.el_slider.find(".ui-slider-handle").on("mousedown ontouchstart", () => {
            this.el_slider.find(".slider-bubble").toggle(true);
            refresh_bubble();
        })
        this.el_slider.find(".ui-slider-handle").on("mouseup focusout ontouchend", async () => {
            await waitout_js_loop()
            this.el_slider.find(".slider-bubble").toggle(false);
            refresh_bubble();
        })

        this.el_slider.find(".ui-slider-handle").on("mouseup ontouchend", async () => {
            let value = this.el_slider.slider('value')
            if (this.contrastive_esa) {
                value = Math.min(10, Math.ceil((value + 0.1) / 10));
            }
            if (this.tutorial) {
                // do nothing, we don't validate during tutorial
            } else if (this.mqm.length == 0 && value < 66) {
                alert(`You assigned a score of ${value} without highlighting any errors. Please, highlight errors first.`)
            }
        })

        this.el_slider.on("slide", async () => {
            this.el_slider.find(".slider-bubble").toggle(true);
            refresh_bubble()
            await waitout_js_loop()
            refresh_bubble()
        });
        // hide by default
        this.el_slider.find(".slider-bubble").toggle(false);

        this.el.find('.button-submit').on("click", (event) => { event.preventDefault(); this.note_change() });
    }

    current_mqm_score(modified) {
        let score = this.mqm.reduce((a, b) => a - SEVERITY_TO_SCORE[b["severity"]], 0)
        if (modified) {
            return (Math.max(-25, score) + 25) * 4
        } else {
            return score
        }
    }

    async redraw_mqm() {
        // store currently displayed version
        this.el.find('input[name="mqm"]').val(JSON.stringify(this.mqm));

        // redraw
        this.el_target.children(".mqm_char").each((i, el) => {
            el = $(el)
            let char_id = Number.parseInt(el.attr("char_id"))

            // render existing mqm
            let active_mqm = this.mqm.map((v, i) => [v, i]).filter((v) => (
                (v[0]["start_i"] <= char_id && v[0]["end_i"] >= char_id) ||
                (el.attr("char_id") == "missing" && v[0]["start_i"] == "missing" && v[0]["end_i"] == "missing")
            ))
            // TODO: should be only 0 or 1 exactly
            if (active_mqm.length > 0) {
                active_mqm = active_mqm[0]
                // Use setProperty with 'important' priority to ensure error colors override diff highlights
                el[0].style.setProperty("background-color", SEVERITY_TO_COLOR[active_mqm[0]["severity"]], "important")
                el.attr("in_mqm", active_mqm[1])

                let tooltip_message = active_mqm[0]["severity"].capitalize();
                if ("error_type" in active_mqm[0]) {
                    (active_mqm[0]["error_type"] || []).forEach((x) => {
                        tooltip_message += " > " + x
                    });
                }
                el.attr("title", tooltip_message)
            } else if (!this.SELECTION_STATE.includes(i)) {
                // reset color - but only remove the style attribute if no diff class present
                // so CSS can apply diff highlighting
                if (el.hasClass('diff-sub') || el.hasClass('diff-ins') || el.hasClass('diff-del')) {
                    // Remove the style attribute entirely to let CSS take over
                    el.removeAttr("style")
                } else {
                    el.css("background-color", "")
                }
            }
        })

        this.check_status()
        
        // Trigger validation for contrastive ESA mode
        if (this.contrastive_esa && typeof validateAndUpdateButtonState === 'function') {
            validateAndUpdateButtonState(this.el);
        }
    }

    reset() {
        this.el.find('.button-submit').toggle(MQM_TYPE == "MQM")
        this.el.attr("data-item-completed", "False")
        this.el_slider.find(".slider-bubble").remove()
        this.initialize()
        // if we reset then we automatically hide the next doc button
        toggle_doc_button(false)
        this.el_slider.slider('value', 0)
    }

    remove_undecided(mqm_object) {
        // remove attribute pointers if they point to undecided spans
        mqm_object.el_target.children(".mqm_char").each((i, el) => {
            if ($(el).attr("in_mqm") && mqm_object.mqm[Number.parseInt($(el).attr("in_mqm"))]["severity"] == "undecided") {
                $(el).removeAttr("in_mqm")
            }
        })
        // clear all undecided
        mqm_object.mqm = mqm_object.mqm.filter(v => v["severity"] != "undecided");
        mqm_object.redraw_mqm()
    }

    check_status() {
        if (this.el.attr("data-item-completed") == "True") {
            _change_item_status_icon(this.el, "ok")
            this.el.find(".button-submit").hide()
        } else {
            _change_item_status_icon(this.el, "flag")
        }
    }

    note_change(mark_complete=true) {
        if (mark_complete) {
            this.el.find('.button-submit').toggle(false)
            this.el.attr("data-item-completed", "True")
        }

        // update counters
        this.update_item_times()
        this.check_status()

        if (mark_complete && _all_sentences_scored()) {
            toggle_doc_button(true)
        }

        return true
    }


    validate_tutorial() {
        if ("mqm_target" in this.tutorial) {
            if (this.tutorial["mqm_target"].length != this.mqm.length) {
                return false
            }
            let fulfilled = this.tutorial["mqm_target"].map((x) => {
                // check that each mqm requirement has a fuzzy match in this.mqm
                return (this.mqm.some(y =>
                    fuzzy_abs_match(y["start_i"], x["start_i"], 3) &&
                    fuzzy_abs_match(y["end_i"], x["end_i"], 3) &&
                    (x["severity"] == y["severity"])
                ))
            })
            if (!fulfilled.every(x => x))
                return false
        }
        if ("score_target" in this.tutorial) {
            // tolerate range of 10, quite a lot
            if (!fuzzy_abs_match(this.tutorial["score_target"], Number.parseFloat(this.el.find("input[name='score']").val()), 20)) {
                return false
            }
        }
        return true
    }

    validate_form() {
        if (this.tutorial && !this.validate_tutorial()) {
            alert(`Please follow the tutorial instructions.\n(${this.text_target_orig.substring(0, 60)}...)`);
            return false
        }
        return true;
    }

    abort_selection() {
        // cleanup
        this.el_target.children(".mqm_char[selected]").each((_, el) => $(el).attr("selected", false))
        this.SELECTION_STATE = []
    }

    update_item_times() {
        // set the start timestamp if it hasn't been touched yet
        $(this.el).find('input[name="start_timestamp"]').val($(this.el).find('input[name="start_timestamp"]').val() || Date.now() / 1000)

        // end timestamp is the latest interaction
        $(this.el).find('input[name="end_timestamp"]').val(Date.now() / 1000)
    }

    // call only once
    setup_span_click_handlers() {
        this.el_target.children(".mqm_char").each((i, el) => {
            el = $(el)
            let char_id = Number.parseInt(el.attr("char_id"))

            // remove undecided spans only when the mouse laves them
            el.on("mouseout", async () => {
                if (el.attr("in_mqm") && this.mqm[Number.parseInt(el.attr("in_mqm"))]["severity"] == "undecided") {
                    this.HOVER_UNDECIDED_SPANS.delete(i)
                    // wait for a bit in case mouse enter adds to this
                    await waitout_js_loop()
                    if (this.HOVER_UNDECIDED_SPANS.size == 0)
                        this.MQM_DELETE_TIMER = setTimeout(() => this.remove_undecided(this), 400)
                    else
                        clearTimeout(this.MQM_DELETE_TIMER)
                }
            })
            el.on("mouseenter", async () => {
                if (el.attr("in_mqm") && this.mqm[Number.parseInt(el.attr("in_mqm"))]["severity"] == "undecided") {
                    this.HOVER_UNDECIDED_SPANS.add(i)
                }
            })

            el.on("click mousedown mouseup", async (event) => {
                // do nothing to prevent all three events operating at the same time
                if (event.timeStamp < this.LAST_MOUSE_TIMESTAMP + 250) {
                    event.preventDefault()
                    return
                }
                this.note_change(MQM_TYPE == "MQM")
                this.LAST_MOUSE_TIMESTAMP = event.timeStamp

                if (el.attr("char_id") == "missing") {
                    this.abort_selection()
                    let mqm_missing = this.mqm.filter(v => v["start_i"] == "missing" && v["end_i"] == "missing")
                    if (mqm_missing.length == 0) {
                        let error_type = await get_error_type()
                        if (MQM_TYPE == "MQM" && error_type == null) {
                            _show_error_box("You need to select error type")
                        } else {
                            // create new missing mqm span
                            mqm_missing = {
                                "start_i": "missing",
                                "end_i": "missing",
                                "severity": "minor",
                                "error_type": error_type,
                            }
                            this.mqm.push(mqm_missing)
                            _show_error_box("Minor")
                        }
                    } else {
                        // increase severity
                        mqm_missing = mqm_missing[0]
                        mqm_missing["severity"] = SEVERITY_TO_NEXT[mqm_missing["severity"]]
                        _show_error_box(mqm_missing["severity"].capitalize())
                    }
                    this.redraw_mqm()
                    return
                }

                if (el.attr("in_mqm")) {
                    if (this.SELECTION_STATE.length != 0) {
                        this.abort_selection()
                        return
                    }
                    let mqm_i = Number.parseInt(el.attr("in_mqm"))
                    this.mqm[mqm_i]["severity"] = SEVERITY_TO_NEXT[this.mqm[mqm_i]["severity"]]
                    _show_error_box(this.mqm[mqm_i]["severity"].capitalize())
                    this.redraw_mqm()
                    this.abort_selection()
                } else {
                    // add new span
                    el.attr("selected", true)
                    this.SELECTION_STATE.push(char_id)
                    // TODO: intermediate highlight on hover?
                    if (this.SELECTION_STATE.length == 2) {
                        // check that nothing overlaps
                        let start_i = Math.min(...this.SELECTION_STATE)
                        let end_i = Math.max(...this.SELECTION_STATE)
                        if (this.mqm.some((v) =>
                            (v["start_i"] > start_i && v["start_i"] < end_i) ||
                            (v["end_i"] > start_i && v["end_i"] < end_i)
                        )) {
                            this.abort_selection()
                            _show_error_box("Overlapping error fragments are not allowed.")
                            return
                        }

                        let error_type = await get_error_type()
                        if (MQM_TYPE == "MQM" && error_type == null) {
                            _show_error_box("You need to select error type")
                        } else {
                            this.mqm.push({
                                "start_i": start_i,
                                "end_i": end_i,
                                "severity": "minor",
                                "error_type": error_type
                            })
                            _show_error_box("Minor")
                        }


                        this.abort_selection()
                        this.redraw_mqm()
                    }
                }
            })
        })
    }
}
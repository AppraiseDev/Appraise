// constants and utils
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
        MQM_HANDLERS[$(el).attr("data-item-id")] = new MQMItemHandler(el)
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
    $("#button-next-doc-fake").toggle(!visible)
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

    
        // setup_span_structure
        let html_target = this.text_target_orig.split("").map((v, i) => {
            if (v == "\n") {
                return "<br>" // preserve newlines
            }
            return `<span class="mqm_char" id="target_char_${i}" char_id="${i}">${v}</span>`
        }).join("") + " <span class='mqm_char span_missing' id='target_char_missing' char_id='missing'>[MISSING]</span>"
        this.el_target.html(html_target)

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
            let html_source = this.text_source_orig.split("").map((v, i) => {
                if (v == "\n") {
                    return "<br>" // preserve newlines
                }
                return `<span class="mqm_char_src" id="source_char_${i}" char_id="${i}">${v}</span>`
            }).join("")
            this.el_source.html(html_source)

            await waitout_js_loop()

            let len_src = this.text_source_orig.split("").length
            let len_tgt = this.text_target_orig.split("").length
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


        // slider bubble handling
        this.el_slider.find(".ui-slider-handle").append("<div class='slider-bubble'>100</div>")
        let refresh_bubble = () => {
            this.el_slider.find(".slider-bubble").text(this.el_slider.slider('value'))
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
                el.css("background-color", SEVERITY_TO_COLOR[active_mqm[0]["severity"]])
                el.attr("in_mqm", active_mqm[1])

                let tooltip_message = active_mqm[0]["severity"].capitalize();
                if ("error_type" in active_mqm[0]) {
                    (active_mqm[0]["error_type"] || []).forEach((x) => {
                        tooltip_message += " > " + x
                    });
                }
                el.attr("title", tooltip_message)
            } else if (!this.SELECTION_STATE.includes(i)) {
                // reset color
                el.css("background-color", "")
            }
        })

        this.check_status()
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
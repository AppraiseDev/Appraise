// constants and utils
const SEVERITY_TO_COLOR = {
    "critical": "#f33c",
    "major": "#f70a",
    "minor": "#dd0a",
    "neutral": "#f993",
    "undecided": "#99d9",
}
const SEVERITY_TO_SCORE = {
    "critical": 15,
    "major": 5,
    "minor": 1,
    "neutral": 0,
    "undecided": Number.NaN,
}
const SEVERITY_TO_NEXT = {
    "neutral": "minor",
    "undecided": "minor",
    "minor": "major",
    "major": "critical",
    "critical": "undecided",
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

$(document).ready(() => {
    MQM_TYPE = JSON.parse($('#mqm-type-payload').html())

    // This sets the same starting time for all items, but it is set again when
    // an item is expanded by clicking on it.
    $('input[name="start_timestamp"]').val(Date.now());

    // bind UI events
    // TODO: this does not work very well because of 
    $('.button-reset').on("click", (event) => {
        MQM_HANDLERS[$(event.target).parents('.item-box').attr("data-item-id")].reset()
    });

    // all except the document-level item send Ajax POST request
    $('.button-submit').on("click", submit_form_local);

    // hide next doc button for now
    $("#button-next-doc").toggle(false)
    $("#button-next-doc").on("click", submit_finish_document)

    $(".item-box").each((_i, el) => {
        MQM_HANDLERS[$(el).attr("data-item-id")] = new MQMItemHandler(el)
        $(el).find('input[name="start_timestamp"]').val(Date.now());
    })

    // highlight instructions
    Object.keys(SEVERITY_TO_COLOR).map((key) => {
        $(`#instruction_sev_${key}`).css("background-color", SEVERITY_TO_COLOR[key])
    })
});

function _all_sentences_scored() {
    let items_left = $('.item-box').filter((_i, el) => $(el).attr('data-item-completed') == "False").length;
    console.log('Items left:', items_left);
    return items_left == 0;
}

function _change_item_status_icon(item_box, icon_name, status_text) {
    let icon_box = item_box.find('.status-indicator').removeClass('glyphicon-refresh glyphicon-ok glyphicon-flag');
    item_box.find(".status-text").text(status_text)
    icon_box.addClass(`glyphicon-${icon_name}`)
}

function submit_form_local(event) {
    // We are doing a manual AJAX request, so stop this
    event.preventDefault();

    let item_box = $(event.target).closest('.item-box');
    let mqm_handler = MQM_HANDLERS[item_box.attr("data-item-id")]

    if (!mqm_handler.validate_form()) {
        return
    }

    // update counters
    item_box.attr("data-item-completed", "True")
    mqm_handler.check_status()

    // hide document submit for now
    item_box.find('button[name="next_button"]').toggle(false);

    // Add end timestamp
    item_box.find('input[name="end_timestamp"]').val(Date.now());

    if (_all_sentences_scored()) {
        $("#button-next-doc").toggle(true)
    } else {
        // $(`#item-${data.item_id}`).get(0).scrollIntoView({ behavior: "smooth" })
    }

    return true
}

function submit_form_ajax(item_box) {
    // let item_box = $(event.target).closest('.item-box');
    let promise = $.ajax({
        data: item_box.find('form').serialize(),
        type: 'POST',
        // post to the same url it was loaded from
        url: '',
        dataType: 'json',
        beforeSend: function () {
            console.log('Sending AJAX request, item-id=', item_box.data('item-id'));
            _change_item_status_icon(item_box, 'refresh', "Uploading");
        },
        success: function (data) {
            console.log('Success, saved=', data.saved, 'next_item=', data.item_id);
            if (data.saved) {


            } else {
                _change_item_status_icon(item_box, 'none', "Upload failed");
                _show_error_box(data.error_msg, 10_000);
            }
        },
        error: function (x, s, t) {
            console.log('Error:', x, s, t);
            _change_item_status_icon(item_box, 'none', "Upload failed");
            _show_error_box(
                'An unrecognized error has occured. ' +
                'Please reload the page or try again in a moment. ',
                5_000
            );
        },
    });

    return promise
}

async function submit_finish_document() {
    // wait for individual items to be submitted
    let promises = [...$(".item-box").map((_i, el) => submit_form_ajax($(el)))]
    await Promise.all(promises)

    // trigger hidden form
    $("#form-next-doc").trigger("submit")
}

function _show_error_box(text, timeout = 2000) {
    let obj = $(`<div class="alert_message" style="display: none">${text}</div>`)
    $("body").append(obj);
    obj.fadeIn(200);
    // disappear in 2s
    setTimeout(() => { obj.fadeOut(700, () => { obj.remove() }) }, timeout);
}


String.prototype.capitalize = function () {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

function fuzzy_abs_match(a, b, tol) {
    return a == b || Math.abs(a - b) <= tol
}

class MQMItemHandler {
    constructor(el) {
        this.el = $(el)
        this.initialize()
    }

    initialize() {
        this.el_target = this.el.find(".target-text")
        this.el_slider = this.el.find('.slider')
        // for Appraise reasons it's a JSON string encoding JSON
        this.mqm = JSON.parse(JSON.parse(this.el.children('#mqm-payload').html()))
        if (!Array.isArray(this.mqm)) {
            this.tutorial = this.mqm["tutorial"]
            this.mqm = this.mqm["payload"]
            this.el.find(".tutorial-text").html(this.tutorial["instruction"])
        } else {
            this.tutorial = false
        }
        this.mqm_submitted = structuredClone(this.mqm)
        this.mqm_orig = JSON.parse(JSON.parse(this.el.children('#mqm-payload-orig').html()))
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
                    this.check_status()
                }
            }
        })

        // setup_span_structure
        let split_text = this.text_target_orig.split("")

        // word-level, not used anymore
        // split_text = [...TXT_CANDIDATE_ORIGINAL.matchAll(/([\p{L}\-0-9]+|[^\p{L}\-0-9]+)/gu)].map((v) => v[0])
        let html_candidate = split_text.map((v, i) => {
            return `<span class="mqm_char" id="candidate_char_${i}" char_id="${i}">${v}</span>`
        }).join("") + " <span class='mqm_char span_missing' id='candidate_char_missing' char_id='missing'>[MISSING]</span>"
        this.el_target.html(html_candidate)

        this.redraw_mqm()

        // call setup only once
        this.setup_span_click_handlers()
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
        // should be in range [0, 100]
        this.el_slider.slider('value', this.current_mqm_score(true))

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
            } else if (!this.SELECTION_STATE.includes(i)) {
                // reset color
                el.css("background-color", "")
            }
        })

        this.check_status()
    }

    reset() {
        this.el.find('button[name="next_button"]').toggle(true);
        this.el.attr("data-item-completed", "False")
        this.initialize()
        // if we reset then we automatically hide the next doc button
        $("#button-next-doc").toggle(false)
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
            _change_item_status_icon(this.el, "ok", "Completed")
        } else {
            _change_item_status_icon(this.el, "flag", "Unfinished")
        }
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
            if (!fuzzy_abs_match(this.tutorial["score_target"], Number.parseFloat(this.el.find("input[name='score']").val()), 10)) {
                return false
            }
        }
        return true
    }

    validate_form() {
        if (this.tutorial && !this.validate_tutorial()) {
            alert('Please follow the tutorial instructions.');
            return false
        }
        // skip other messages in the tutorial
        if (this.tutorial) {
            return true
        }

        if (this.mqm.some((x) => x["severity"] == "undecided")) {
            alert('There are some segments without severity (in blue). Click on them to change their severities.');
            return false
        }
        if (this.mqm.length == 0 && !confirm("There are no annotated text fragments. Are you sure you want to submit?")) {
            return false
        }
        if (this.current_mqm_score(true) == Number.parseFloat(this.el.find("input[name='score']").val()) && !confirm("You did not change the original translation score. Are you sure you want to submit?")) {
            return false
        }
        return true;
    }

    abort_selection() {
        // cleanup
        this.el_target.children(".mqm_char[selected]").each((_, el) => $(el).attr("selected", false))
        this.SELECTION_STATE = []
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
                        this.MQM_DELETE_TIMER = setTimeout(() => this.remove_undecided(this), 1000)
                    else
                        clearTimeout(this.MQM_DELETE_TIMER)
                }
            })
            el.on("mouseenter", async () => {
                if (el.attr("in_mqm") && this.mqm[Number.parseInt(el.attr("in_mqm"))]["severity"] == "undecided") {
                    this.HOVER_UNDECIDED_SPANS.add(i)
                }
            })

            el.on("click mousedown mouseup", (event) => {
                // do nothing to prevent all three events operating at the same time
                if (event.timeStamp < this.LAST_MOUSE_TIMESTAMP + 250) {
                    event.preventDefault()
                    return
                }
                this.LAST_MOUSE_TIMESTAMP = event.timeStamp

                if (el.attr("char_id") == "missing") {
                    this.abort_selection()
                    let mqm_missing = this.mqm.filter(v => v["start_i"] == "missing" && v["end_i"] == "missing")
                    if (mqm_missing.length == 0) {
                        // create new missing mqm span
                        mqm_missing = {
                            "start_i": "missing",
                            "end_i": "missing",
                            "severity": "minor",
                        }
                        this.mqm.push(mqm_missing)
                        _show_error_box("Minor")
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

                        this.mqm.push({
                            "start_i": start_i,
                            "end_i": end_i,
                            "severity": "minor",
                        })
                        _show_error_box("Minor")


                        this.abort_selection()
                        this.redraw_mqm()
                    }
                }
            })
        })
    }
}
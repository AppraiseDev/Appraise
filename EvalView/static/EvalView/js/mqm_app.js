var MQM = {
    elements: {
        tags: null
    },
    constants: {
        errors: {
            MISSING_FIELDS: {
                heading: "Error Category is Missing",
                message: "Please make sure you specify an error category"
            },
            INSUFFICIENT_CHARS: {
                heading: "Insufficient Characters",
                message: "Please select at least 10 characters"
            }
        }
    },
    variables: {
        messageDisplayed: false
    },
    helpers: {
        resetControls: function() {
            MQM.elements.tags.dropdown("clear").dropdown("set text", "Select Tag");
            $("#mqm-text").text("");
        },
        showBackdrop: function(isShown) {
            $(".backdrop")[isShown ? "show" : "hide"]();
        },
        showError: function(error) {
            if (!MQM.variables.messageDisplayed) {
                MQM.variables.messageDisplayed = true;

                $("#error_message").find(".header").html(error.heading);
                $("#error_message").find(".message").html(error.message);

                $("#error_message").transition("fly down");

                window.setTimeout(
                    function() {
                        MQM.variables.messageDisplayed = false;

                        $("#error_message").transition("fly up");
                    },
                    5000
                );
            }
        }
    },
    handlers: {
        fillNotes: function(selection) {
            // TODO: make #mqm-text configurable
            $("#mqm-text").text(selection).trigger("change");
        },
        captureNotes: function(text) {
            $.Annotator.api.captureActiveAnnotationNotes(text.innerText);
        },
        applyTag: function(tagName) {
            $.Annotator.api.tagActiveAnnotation(tagName);
        },
        identifyItem: function(itemId) {
            $.Annotator.api.identifyActiveAnnotation(itemId);
        },
        cancelAnnotation: function() {
            MQM.helpers.resetControls();
            MQM.helpers.showBackdrop(false);

            $.Annotator.api.destroyActiveAnnotation();
        },
        saveAnnotation: function() {
            var result = $.Annotator.api.saveActiveAnnotation();

            if (!result.isSaved) {
                MQM.helpers.showError(MQM.constants.errors[result.errorCode]);
            } else {
                MQM.helpers.resetControls();
                MQM.helpers.showBackdrop(false);
            }
        },
        renderSavedAnnotations: function(annotationsAll, itemId) {
            console.log("Annotations (all+filtered)");
            console.log(annotationsAll);

            annotations = annotationsAll.filter(a => a.item === itemId);
            console.log(annotations);

            // TODO: select annotations for itemId and render only those
            var html = $.templates("#annotations_tmpl").render({
                annotations: annotations.map((item) => {
                    // TODO: make this configurable!
                    if (item.type === "accuracy") {
                        item.color = "orange";
                    } else if (item.type === "fluency") {
                        item.color = "teal";
                    } else if (item.type === "terminology") {
                        item.color = "blue";
                    } else if (item.type === "style") {
                        item.color = "yellow";
                    } else if (item.type === "locale") {
                        item.color = "green";
                    } else if (item.type === "other") {
                        item.color = "grey";
                    } else if (item.type === "source") {
                        item.color = "pink";
                    } else if (item.type === "nontranslation") {
                        item.color = "red";
                    } else {
                        item.color = "olive";
                    }

                    return item;
                })
            });

            $("#" + itemId).find(".mqm-annotation-list").html(html);
        },
        deleteAnnotation: function(annotationId, itemId) {
            var remainingAnnotations = $.Annotator.api.deleteAnnotation(annotationId);
            console.log("Deleting " + annotationId);
            MQM.handlers.renderSavedAnnotations(remainingAnnotations, itemId);
        }
    },
    init: function() {
        $(".example").annotator({
            popoverContents: "#annotate_settings",
            minimumCharacters: 1,
            makeTextEditable: true,
            onannotationsaved: function() {
                MQM.handlers.renderSavedAnnotations(this.annotations, this.activeItem);
            },
            onselectioncomplete: function() {
                MQM.handlers.fillNotes(this.innerText);
                var itemId = this.closest(".item-box").id;
                MQM.handlers.identifyItem(itemId);
                MQM.helpers.showBackdrop(true);
            },
            onerror: function() {
                MQM.helpers.showError(MQM.constants.errors[this]);
            }
        });

        MQM.elements.tags = $(".ui.dropdown")
            .dropdown({
                clearable: true,
                direction: "upward",
                onChange: function(value, text, $choice) {
                    if ($choice)
                        MQM.handlers.applyTag($choice.attr("name"));
                }
            });
    }
};

MQM.init();

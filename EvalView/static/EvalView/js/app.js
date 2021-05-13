var App = {
    elements: {
        tags: null
    },
    constants: {
        errors: {
            MISSING_FIELDS: {
                heading: "Required Fields Missing",
                message: "Please make sure you specify a Note and select a Tag"
            },
            INSUFFICIENT_CHARS: {
                heading: "Insufficient Characters",
                message: "Please select atleast 10 characters"
            }
        }
    },
    variables: {
        messageDisplayed: false
    },
    helpers: {
        resetControls: function() {
            App.elements.tags.dropdown("clear").dropdown("set text", "Select Tag");
            $("textarea").val("");
        },
        showBackdrop: function(isShown) {
            $(".backdrop")[isShown ? "show" : "hide"]();
        },
        showError: function(error) {
            if (!App.variables.messageDisplayed) {
                App.variables.messageDisplayed = true;

                $("#error_message").find(".header").html(error.heading);
                $("#error_message").find(".message").html(error.message);

                $("#error_message").transition("fly down");

                window.setTimeout(
                    function() {
                        App.variables.messageDisplayed = false;

                        $("#error_message").transition("fly up");
                    },
                    5000
                );
            }
        }
    },
    handlers: {
        fillNotes: function(selection) {
            $("textarea").val(selection).trigger("change");
        },
        captureNotes: function(text) {
            $.Annotator.api.captureActiveAnnotationNotes(text.value);
        },
        applyTag: function(tagName) {
            $.Annotator.api.tagActiveAnnotation(tagName);
        },
        cancelAnnotation: function() {
            App.helpers.resetControls();
            App.helpers.showBackdrop(false);

            $.Annotator.api.destroyActiveAnnotation();
        },
        saveAnnotation: function() {
            var result = $.Annotator.api.saveActiveAnnotation();

            if (!result.isSaved) {
                App.helpers.showError(App.constants.errors[result.errorCode]);
            } else {
                App.helpers.resetControls();
                App.helpers.showBackdrop(false);
            }
        },
        renderSavedAnnotations: function(annotations) {
            var html = $.templates("#annotations_tmpl").render({
                annotations: annotations.map((item) => {
                    if (item.type === "Requirement") {
                        item.color = "orange";
                    } else if (item.type === "Backlog") {
                        item.color = "teal";
                    } else {
                        item.color = "blue";
                    }

                    return item;
                })
            });

            $("#annotations_list").html(html);
        },
        deleteAnnotation: function(annotationId) {
            var remainingAnnotations =
                $.Annotator.api.deleteAnnotation(annotationId);

            App.handlers.renderSavedAnnotations(remainingAnnotations);
        }
    },
    init: function() {
        $(".example").annotator({
            popoverContents: "#annotate_settings",
            minimumCharacters: 1,
            makeTextEditable: true,
            onannotationsaved: function() {
                App.handlers.renderSavedAnnotations(this.annotations);
            },
            onselectioncomplete: function() {
                App.handlers.fillNotes(this.outerText);
                App.helpers.showBackdrop(true);
            },
            onerror: function() {
                App.helpers.showError(App.constants.errors[this]);
            }
        });

        App.elements.tags = $(".ui.dropdown")
            .dropdown({
                clearable: true,
                direction: "upward",
                onChange: function(value, text, $choice) {
                    if ($choice)
                        App.handlers.applyTag($choice.attr("name"));
                }
            });
    }
};

App.init();

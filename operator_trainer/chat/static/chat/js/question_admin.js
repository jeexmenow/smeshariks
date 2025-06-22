if (!window.console) {
    window.console = { log: function() {} };
}

document.addEventListener('DOMContentLoaded', function() {
    (function($) {
        $(document).ready(function() {
            console.log("Custom admin JS loaded for Question model.");

            var isMultiStepCheckbox = $('#id_is_multi_step');
            var maxStepsRow = $('.form-row.field-max_steps');
            var stopWordsRow = $('.form-row.field-stop_words');

            function toggleMultiStepFields() {
                if (isMultiStepCheckbox.is(':checked')) {
                    maxStepsRow.show();
                    stopWordsRow.show();
                } else {
                    maxStepsRow.hide();
                    stopWordsRow.hide();
                }
            }

            // Initial check
            toggleMultiStepFields();

            // Toggle on change
            isMultiStepCheckbox.change(toggleMultiStepFields);
        });
    })(django.jQuery);
}); 
(function($) {
    window.SkipLogic = function (opts) {
        var validSkipSelectors = opts['validSkipSelectors'];
        return function(prefix) {
            var splitPrefix = prefix.split('-');
            var fieldPrefix = splitPrefix[0];
            var fieldID = [fieldPrefix, splitPrefix[1]].join('-');

            var skipLogicSelect = $('#' + prefix + '-skip_logic');
            var skipLogicForm = $('#' + prefix + '-form');
            var skipLogicChoice = $('#' + prefix + '-choice');
            var questionWidgetID = '#' + prefix + '-question';
            var questionSelect = $(questionWidgetID + '_1');
            var questionID = $(questionWidgetID + '_0');

            var thisQuestion = question(fieldID);

            var updateQuestionFormDisplay = function () {
                hideElement(skipLogicForm);
                hideElement(questionSelect);
                switch (skipLogicSelect.val()) {
                    case 'form':
                        showElement(skipLogicForm);
                        break;
                    case 'question':
                        showElement(questionSelect);
                        break;
                    default:
                        break;
                }
            };

            var populateQuestions = function () {
                for (let question of allQuestions(fieldPrefix)) {
                    var sortOrder = question.sortOrder();
                    var label = question.label().val();
                    var selected = sortOrder == questionID.val() ? 'selected' : '';
                    if (thisQuestion.sortOrder() < sortOrder) {
                        questionSelect.append(
                            `<option value="${sortOrder}" ${selected}>${label}</option>`
                        );
                    }
                }
            };

            var hideElement = function(element) {
                element.closest('li').hide();
            };

            var showElement = function(element) {
                element.closest('li').show();
            };

            var updateChoiceLogicDisplay = function() {
                var shouldShowSkipLogic = validSkipSelectors.indexOf(thisQuestion.fieldSelect().val()) >= 0;
                if (!shouldShowSkipLogic) {
                    hideElement(skipLogicSelect);
                    showElement(skipLogicChoice);
                } else if (thisQuestion.fieldSelect().val() == 'checkbox') {
                    showElement(skipLogicSelect);
                    hideElement(skipLogicChoice);
                } else {
                    showElement(skipLogicChoice);
                    showElement(skipLogicSelect);
                }
                updateQuestionFormDisplay();
            };

            updateChoiceLogicDisplay();
            populateQuestions();

            skipLogicSelect.change( function () {
                updateQuestionFormDisplay();
            });
            thisQuestion.fieldSelect().change( function () {
                updateChoiceLogicDisplay();
            });
        };
    };
})(jQuery);

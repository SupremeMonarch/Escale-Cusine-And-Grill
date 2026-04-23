// progress.js - Cumulative Progress Indicator with Connectors

function updateProgress(currentStep) {
    // progress update (no debug logs)
    
    // Reset all steps to inactive first
    $('[data-step]').removeClass('bg-amber-600').addClass('bg-gray-400');
    
    // Activate all steps up to and including current step
    for (let step = 1; step <= currentStep; step++) {
        const $stepElement = $(`[data-step="${step}"]`);
        if ($stepElement.length) {
            $stepElement.removeClass('bg-gray-400').addClass('bg-amber-600');
            // step activated
        }
    }
    
    // Update connector lines
    updateConnectorLines(currentStep);
}

function updateConnectorLines(currentStep) {
    // update connector lines
    
    // Get all connector lines
    $('[data-connector]').each(function () {
        const $connector = $(this);
        const connectorStep = parseInt($connector.attr('data-connector'), 10);
        
        // Connector lines should be amber if they come BEFORE the current step
        if (connectorStep < currentStep) {
            $connector.removeClass('bg-gray-400').addClass('bg-amber-600');
            // connector set to amber
        } else {
            $connector.removeClass('bg-amber-600').addClass('bg-gray-400');
            // connector set to gray
        }
    });
}

$(function () {
    if (typeof CURRENT_STEP !== 'undefined') {
        updateProgress(parseInt(CURRENT_STEP));
    } else {
        updateProgress(1); // fallback
    }
});

window.updateProgress = updateProgress;
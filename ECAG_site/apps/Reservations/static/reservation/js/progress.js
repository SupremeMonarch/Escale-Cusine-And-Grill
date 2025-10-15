// progress.js - Cumulative Progress Indicator with Connectors

function updateProgress(currentStep) {
    console.log("Updating progress to step:", currentStep);
    
    // Reset all steps to inactive first
    const steps = document.querySelectorAll('[data-step]');
    steps.forEach(step => {
        step.classList.remove('bg-amber-600');
        step.classList.add('bg-gray-400');
    });
    
    // Activate all steps up to and including current step
    for (let step = 1; step <= currentStep; step++) {
        const stepElement = document.querySelector(`[data-step="${step}"]`);
        if (stepElement) {
            stepElement.classList.remove('bg-gray-400');
            stepElement.classList.add('bg-amber-600');
            console.log(`Step ${step} activated`);
        }
    }
    
    // Update connector lines
    updateConnectorLines(currentStep);
}

function updateConnectorLines(currentStep) {
    console.log("Updating connector lines for step:", currentStep);
    
    // Get all connector lines
    const connectors = document.querySelectorAll('[data-connector]');
    
    connectors.forEach(connector => {
        const connectorStep = parseInt(connector.getAttribute('data-connector'));
        
        // Connector lines should be amber if they come BEFORE the current step
        if (connectorStep < currentStep) {
            connector.classList.remove('bg-gray-400');
            connector.classList.add('bg-amber-600');
            console.log(`Connector ${connectorStep} set to amber`);
        } else {
            connector.classList.remove('bg-amber-600');
            connector.classList.add('bg-gray-400');
            console.log(`Connector ${connectorStep} set to gray`);
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded - CURRENT_STEP:", CURRENT_STEP);
    if (typeof CURRENT_STEP !== 'undefined') {
        updateProgress(parseInt(CURRENT_STEP));
    } else {
        updateProgress(1); // fallback
    }
});

window.updateProgress = updateProgress;
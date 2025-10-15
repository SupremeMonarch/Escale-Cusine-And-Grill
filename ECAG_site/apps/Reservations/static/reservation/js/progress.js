// progress.js - Simple Progress Indicator

function updateProgress(currentStep) {
    // Reset all steps to inactive
    const steps = document.querySelectorAll('[data-step]');
    steps.forEach(step => {
        step.classList.remove('bg-amber-600');
        step.classList.add('bg-gray-500');
    });
    
    // Set current step to active
    const currentStepElement = document.querySelector(`[data-step="${currentStep}"]`);
    if (currentStepElement) {
        currentStepElement.classList.remove('bg-gray-500');
        currentStepElement.classList.add('bg-amber-600');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateProgress(1);
});

window.updateProgress = updateProgress;
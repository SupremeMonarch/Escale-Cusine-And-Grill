document.addEventListener('DOMContentLoaded', function() {
    const sidebarButton = document.getElementById('sidebar-button');
    const orderSidebar = document.getElementById('order-sidebar');
    
    sidebarButton.addEventListener('click', function() {
        orderSidebar.classList.toggle('translate-x-full');
    });
});
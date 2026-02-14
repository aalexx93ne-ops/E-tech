document.addEventListener("DOMContentLoaded", function () {
    const menuIcon = document.querySelector(".menu_icon");
    const menu = document.querySelector(".menu");
    const menuContent = document.querySelector(".menu-content");

    if (!menuIcon || !menu) {
        console.error("Не найден элемент меню!");
        return;
    }

    menuIcon.addEventListener("click", function () {
        const isExpanded = menuIcon.getAttribute("aria-expanded") === "true";
        menu.classList.toggle("open");
        menuIcon.classList.toggle("open");
        menuIcon.setAttribute("aria-expanded", !isExpanded);
    });

    menu.addEventListener("click", function (e) {
        if (!menuContent.contains(e.target) || e.target.tagName === "A") {
            menu.classList.remove("open");
            menuIcon.classList.remove("open");
            menuIcon.setAttribute("aria-expanded", "false");
        }
    });
});

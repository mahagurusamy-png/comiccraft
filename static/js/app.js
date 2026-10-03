const form = document.getElementById("comicForm");

if (form) {

    form.addEventListener("submit", () => {

        const button =
            form.querySelector("button");

        if (button) {

            button.disabled = true;

            button.textContent =
                "Generating your comic... Please wait.";

        }

    });

}
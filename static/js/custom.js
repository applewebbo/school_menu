// Close the modal after successfully submitting the form
htmx.on("htmx:beforeSwap", (e) => {
  // Empty response targeting #dialog => hide the modal
  if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
    window.dispatchEvent(new Event('hide-modal'))
    e.detail.shouldSwap = false
  }
})

// Reinitialize Alpine.js components after each HTMX request
htmx.on('htmx:afterSettle', function(evt) {
  document.querySelectorAll('[x-data]').forEach(el => {
      Alpine.initTree(el);
  });
});

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

// Swipe left to switch between own and favorite school menu (mobile)
document.addEventListener('alpine:init', () => {
  Alpine.data('swipeSchool', () => ({
    touchX: 0,
    touchY: 0,
    onTouchStart(event) {
      this.touchX = event.changedTouches[0].clientX;
      this.touchY = event.changedTouches[0].clientY;
    },
    onTouchEnd(event) {
      const deltaX = event.changedTouches[0].clientX - this.touchX;
      const deltaY = event.changedTouches[0].clientY - this.touchY;
      // Only right-to-left swipes trigger the switch, so the gesture never
      // collides with the browser's left-to-right back-navigation swipe.
      const isLeftSwipe = deltaX < -60 && Math.abs(deltaX) > Math.abs(deltaY) * 2;
      if (isLeftSwipe) {
        this.$refs.switchSchoolBtn?.click();
      }
    },
  }));
});

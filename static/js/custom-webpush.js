// Anonymous subscription for a specific school
window.webPushSubscribeAnonymous = function(registration, options) {
  if (!('PushManager' in window)) {
    alert('Push notifications are not supported by your browser.');
    return;
  }
  registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(options.vapidKey)
  }).then(function(subscription) {
    // Send subscription to the anonymous endpoint
    fetch('/notifications/save-anon-subscription/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subscription: subscription.toJSON(),
        school_id: options.schoolId
      })
    }).then(response => response.json()).then(data => {
      if (data.success) {
        alert('Notifiche push anonime abilitate!');
      } else {
        alert('Errore durante la registrazione anonima: ' + (data.error || 'Errore sconosciuto'));
      }
    });
  }).catch(function(err) {
    alert('Impossibile abilitare le notifiche push: ' + err);
  });
};

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

document.addEventListener('alpine:init', () => {
  Alpine.data('pushNotifications', () => ({
    enabled: false,
    error: '',
    success: '',
    subscribing: false,
    async subscribeAndSubmit(formElement, vapidKey) {
      this.error = '';
      this.subscribing = true;
      if (!('serviceWorker' in navigator)) {
        this.error = 'Push notifications are not supported by your browser.';
        this.subscribing = false;
        return;
      }
      try {
        const registration = await navigator.serviceWorker.ready;

        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidKey)
        });

        const subscriptionString = JSON.stringify(subscription);

        let hiddenInput = formElement.querySelector('input[name="subscription_info"]');
        if (hiddenInput) {
            hiddenInput.value = subscriptionString;
        } else {
            const newInput = document.createElement('input');
            newInput.type = 'hidden';
            newInput.name = 'subscription_info';
            newInput.value = subscriptionString;
            formElement.appendChild(newInput);
        }

        htmx.trigger(formElement, 'submit');
      } catch (err) {
        this.error = 'Impossibile abilitare le notifiche push: ' + err;
      } finally {
        this.subscribing = false;
      }
    }
  }))
});

// Minimal webpush.js for django-webpush subscription
window.webPushSubscribe = function(registration, options) {
  if (!('PushManager' in window)) {
    alert('Push notifications are not supported by your browser.');
    return;
  }
  registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(options.vapidKey)
  }).then(function(subscription) {
    // Send subscription to the server (authenticated)
    fetch('/webpush/save_information/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({
        subscription: subscription.toJSON(),
        user_id: options.userId
      })
    });
    alert('Notifiche push abilitate!');
  }).catch(function(err) {
    alert('Impossibile abilitare le notifiche push: ' + err);
  });
};

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

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener('alpine:init', () => {
  Alpine.data('pushNotifications', () => ({
    enabled: false,
    error: '',
    success: '',
    subscribing: false,
    async subscribe(vapidKey, userId) {
      this.error = '';
      this.success = '';
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
        await fetch('/webpush/save_information/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            subscription: subscription.toJSON(),
            user_id: userId
          })
        });
        this.success = 'Notifiche push abilitate!';
        this.enabled = true;
      } catch (err) {
        this.error = 'Impossibile abilitare le notifiche push: ' + err;
      } finally {
        this.subscribing = false;
      }
    },
    async subscribeAnonymous(vapidKey, schoolId) {
      this.error = '';
      this.success = '';
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
        const response = await fetch('/notifications/save-anon-subscription/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            subscription: subscription.toJSON(),
            school_id: schoolId
          })
        });
        const data = await response.json();
        if (data.success) {
          this.success = 'Notifiche push anonime abilitate!';
          this.enabled = true;
        } else {
          this.error = data.error || 'Errore durante la registrazione anonima.';
        }
      } catch (err) {
        this.error = 'Impossibile abilitare le notifiche push: ' + err;
      } finally {
        this.subscribing = false;
      }
    }
  }))
});

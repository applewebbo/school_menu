function pwaInstallPrompt() {
    return {
        isStandalone: false,
        canPrompt: false,
        deferredPrompt: null,
        isIOS: false,
        isMacOS: false,
        isAndroid: false,
        isWindows: false,
        browserName: "",
        osName: "",
        unsupportedMessage: "",
        installMessage: "",
        checkStandalone() {
            this.isStandalone = window.matchMedia('(display-mode: standalone)').matches
                || window.navigator.standalone === true;
            const ua = window.navigator.userAgent.toLowerCase();

            // Sistema operativo
            this.isIOS = /iphone|ipad|ipod/.test(ua);
            this.isAndroid = /android/.test(ua);
            this.isWindows = /windows/.test(ua);
            // MacOS solo se Safari su Mac (no Chrome, Edge, Vivaldi, Brave, Opera)
            const isMacPlatform = (
                (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1) ||
                (/macintosh|macintel|macppc|mac68k|macos/.test(window.navigator.platform.toLowerCase()))
            );
            this.isMacOS = isMacPlatform && !this.isIOS;
            this.osName = this.isIOS ? "iOS" : this.isAndroid ? "Android" : this.isWindows ? "Windows" : this.isMacOS ? "MacOS" : "Altro";

            // Log di debug per la rilevazione
            console.log("UserAgent:", ua);
            console.log("navigator.platform:", navigator.platform);
            console.log("isIOS:", this.isIOS);
            console.log("isAndroid:", this.isAndroid);
            console.log("isWindows:", this.isWindows);
            console.log("isMacPlatform:", isMacPlatform);
            console.log("isMacOS:", this.isMacOS);

            // Browser detection
            if (ua.includes("opr") || ua.includes("opera")) {
                this.browserName = "Opera";
            } else if (ua.includes("vivaldi")) {
                this.browserName = "Vivaldi";
            } else if (ua.includes("crios") || ua.includes("chrome")) {
                this.browserName = "Chrome";
            } else if (ua.includes("fxios") || ua.includes("firefox")) {
                this.browserName = "Firefox";
            } else if (ua.includes("edgios") || ua.includes("edg")) {
                this.browserName = "Edge";
            } else if (ua.includes("safari")) {
                this.browserName = "Safari";
            } else if (ua.includes("brave")) {
                this.browserName = "Brave";
            } else {
                this.browserName = "Altro";
            }

            console.log("browserName:", this.browserName);
            console.log("osName:", this.osName);

            // Messaggi di supporto
            this.unsupportedMessage = "";
            if (this.isIOS) {
                if (this.browserName !== "Safari") {
                    this.unsupportedMessage = "Il browser che stai usando su iOS non è supportato. Usa Safari per installare la web app.";
                }
            } else if (this.isMacOS) {
                if (this.browserName === "Safari") {
                    // messaggio già presente
                } else if (["Chrome", "Vivaldi"].includes(this.browserName)) {
                    // messaggio già presente
                } else {
                    this.unsupportedMessage = "Il browser che stai usando su Mac non è supportato. Usa Safari per installare la web app.";
                }
            } else if (this.isAndroid) {
                if (this.browserName === "Chrome") {
                    // messaggio già presente
                } else if (this.browserName === "Opera") {
                    this.installMessage = "Per aggiungere questa web app su Opera, apri il menu e scegli 'Aggiungi a schermata Home'.";
                } else {
                    this.unsupportedMessage = "Il browser che stai usando su Android non è supportato. Usa Chrome per installare la web app.";
                }
            } else if (this.isWindows) {
                if (["Edge", "Chrome"].includes(this.browserName)) {
                    // messaggio già presente
                } else {
                    this.unsupportedMessage = "Il browser che stai usando su Windows non è supportato. Usa Chrome per installare la web app.";
                }
            }
            this.installMessage = this.installMessage || "";
            window.addEventListener("beforeinstallprompt", (e) => {
                e.preventDefault();
                this.deferredPrompt = e;
                this.canPrompt = true;
            });
        },
        async showPrompt() {
            if (this.deferredPrompt) {
                this.deferredPrompt.prompt();
                const { outcome } = await this.deferredPrompt.userChoice;
                if (outcome === "accepted") {
                    this.installMessage = "App installata!";
                    this.checkStandalone(); // Aggiorna subito lo stato dopo installazione
                } else {
                    this.installMessage = "Installazione annullata.";
                }
                this.canPrompt = false;
                this.deferredPrompt = null;
            }
        }
    }
}

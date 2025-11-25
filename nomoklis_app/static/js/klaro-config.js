// By default, Klaro will load the config from a global variable
// called `klaroConfig`. If that variable does not exist, it will
// load the config from a file called `klaro-config.js`.
// We will define it here.
//
// You can see the full config reference here:
// https://klaro.kiprotect.com/docs/getting-started/configuration
var klaroConfig = {
    // Show the modal without prior user interaction, i.e. without the
    // user having clicked on a link with class "klaro".
    mustConsent: true,

    // Setting this to true will directly display the consent manager modal.
    showModal: true,

    // You can customize the ID of the DIV element that Klaro will create
    // when starting up. If undefined, Klaro will use 'klaro'.
    elementID: 'klaro',

    // You can override the CSS style of Klaro. For a list of CSS variables,
    // see the CSS reference. If you override the style, you should perhaps
    // also disable the default style load below.
    styling: {
        theme: ['light', 'bottom', 'wide'],
    },

    // Setting this to true will disable Klaro's completely.
    disabled: false,

    // You can render the consent notice and manager in a specific language.
    // If undefined, Klaro will use the browser's language preferences.
    lang: 'lt',

    // You can overwrite existing translations or add new ones.
    // For a list of available translations, see the internationalization
    // documentation.
    translations: {
        lt: {
            consentModal: {
                title: 'Slapukai, kuriuos norėtume naudoti',
                description:
                    'Čia galite peržiūrėti ir pritaikyti, kokias paslaugas norėtume naudoti šioje svetainėje.',
                privacyPolicy: {
                    text: 'Daugiau informacijos rasite mūsų {privacyPolicy}.',
                    name: 'privatumo politikoje',
                }
            },
            consentNotice: {
                title: 'Ši svetainė naudoja slapukus',
                description: 'Mes naudojame slapukus, kad galėtume teikti paslaugas ir analizuoti srautą. Informacija apie jūsų naudojimąsi mūsų svetaine yra bendrinama su mūsų partneriais. Jie gali ją sujungti su kita informacija, kurią jiems pateikėte arba kurią jie surinko jums naudojantis jų paslaugomis.',
                learnMore: 'Sužinoti daugiau',
            },
            ok: 'Gerai',
            acceptSelected: 'Priimti pasirinktus',
            acceptAll: 'Priimti visus',
            decline: 'Atmesti',
            close: 'Uždaryti',
            purposes: {
                necessary: 'Būtini',
                statistics: 'Statistika',
            },
            services: {
                'session-cookie': {
                    title: 'Sesijos slapukas',
                    description: 'Būtinasis Django sesijos slapukas, reikalingas vartotojo autentifikavimui.',
                },
                'csrftoken-cookie': {
                    title: 'CSRF ženklas',
                    description: 'Apsaugo nuo Cross-Site Request Forgery (CSRF) atakų.',
                },
                analytics: {
                    title: 'Statistika (neprivaloma)',
                    description: 'Anoniminiai duomenys apie naudojimąsi svetaine, skirti tobulinti paslaugas.',
                },
            },
        },
    },

    // This is a list of third-party services that Klaro will manage for you.
    services: [
        {
            name: 'session-cookie',
            default: true,
            required: true,
            purpose: 'necessary',
            cookies: ['sessionid'],
        },
        {
            name: 'csrftoken-cookie',
            default: true,
            required: true,
            purpose: 'necessary',
            cookies: ['csrftoken'],
        },
        {
            name: 'analytics',
            default: true, // Vartotojas nori, kad pagal nutylėjimą būtų įjungta
            purpose: 'statistics',
            // Įrašykite čia savo analizės įrankio slapukų pavadinimus, pvz.:
            // cookies: ['_ga', '_gid'],
            cookies: [], 
            // callback: function(consent, app) {
            //     if (consent) {
            //         // čia įterpkite savo analizės kodą
            //     }
            // },
        },
    ],
};

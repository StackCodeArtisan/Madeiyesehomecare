// static/js/main.js - Client-side interactions for MedaiyeseHomeCareServices
const form = document.getElementById('careRequestForm');
const submitBtn = document.getElementById('submitBtn');
const spinner = document.getElementById('formSpinner');
const alertBox = document.getElementById('formAlert');
const csrfInput = document.getElementById('csrfToken');
const honeypotInput = document.getElementById('serviceInterest');
const scrollBtn = document.getElementById('scrollToForm');
const currentYear = document.getElementById('year');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const appointmentForm = document.getElementById('appointmentForm');
const appointmentAlert = document.getElementById('appointmentAlert');
const appointmentCsrfInput = document.getElementById('appointmentCsrfToken');
const appointmentSubmitBtn = document.getElementById('appointmentSubmitBtn');
const appointmentSpinner = document.getElementById('appointmentSpinner');
const appointmentHoneypot = document.getElementById('appointmentGuard');

function toggleSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    if (isSubmitting) {
        spinner.classList.remove('d-none');
    } else {
        spinner.classList.add('d-none');
    }
}

function showAlert(message, type = 'success') {
    if (!alertBox) return;
    alertBox.className = `alert alert-${type}`;
    alertBox.textContent = message;
}

function clearForm() {
    form.reset();
    honeypotInput.value = '';
}

function validateClientSide(data) {
    const errors = [];
    ['full_name', 'phone', 'email', 'address', 'start_date', 'care_type'].forEach((field) => {
        if (!data[field]) {
            errors.push('Please fill in all required fields.');
        }
    });
    if (data.email && !EMAIL_PATTERN.test(data.email)) {
        errors.push('Provide a valid email address.');
    }
    return errors;
}

async function submitForm(event) {
    event.preventDefault();
    if (!form || submitBtn.disabled) return;

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    payload.csrf_token = csrfInput.value;

    const errors = validateClientSide(payload);
    if (errors.length) {
        showAlert(errors[0], 'warning');
        return;
    }

    toggleSubmitting(true);
    showAlert('Submitting your request…', 'info');

    try {
        const response = await fetch('/request-care', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (result.csrf_token) {
            csrfInput.value = result.csrf_token;
        }

        if (!response.ok || !result.success) {
            const message = result.message || 'Something went wrong. Please try again.';
            showAlert(message, 'danger');
            return;
        }

        showAlert(result.message || 'Request sent. We will contact you soon!', 'success');
        clearForm();
    } catch (error) {
        console.error('Submission error', error);
        showAlert('Network error. Please try again shortly.', 'danger');
    } finally {
        toggleSubmitting(false);
    }
}

function toggleAppointmentSubmitting(isSubmitting) {
    if (!appointmentSubmitBtn || !appointmentSpinner) return;
    appointmentSubmitBtn.disabled = isSubmitting;
    appointmentSpinner.classList.toggle('d-none', !isSubmitting);
}

function showAppointmentAlert(message, type = 'success') {
    if (!appointmentAlert) return;
    appointmentAlert.className = `alert alert-${type}`;
    appointmentAlert.textContent = message;
}

function validateAppointmentData(data) {
    const errors = [];
    ['full_name', 'email', 'phone', 'preferred_date', 'preferred_time'].forEach((field) => {
        if (!data[field]) {
            errors.push('Please complete all required appointment fields.');
        }
    });
    if (data.email && !EMAIL_PATTERN.test(data.email)) {
        errors.push('Provide a valid email address.');
    }
    return errors;
}

async function submitAppointment(event) {
    event.preventDefault();
    if (!appointmentForm || appointmentSubmitBtn.disabled) return;

    const formData = new FormData(appointmentForm);
    const payload = Object.fromEntries(formData.entries());
    payload.csrf_token = appointmentCsrfInput ? appointmentCsrfInput.value : '';

    const errors = validateAppointmentData(payload);
    if (errors.length) {
        showAppointmentAlert(errors[0], 'warning');
        return;
    }

    toggleAppointmentSubmitting(true);
    showAppointmentAlert('Submitting your appointment request…', 'info');

    try {
        const response = await fetch('/submit-appointment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (result.csrf_token && appointmentCsrfInput) {
            appointmentCsrfInput.value = result.csrf_token;
        }

        if (!response.ok || !result.success) {
            const message = result.message || 'Unable to schedule right now. Please try again.';
            showAppointmentAlert(message, 'danger');
            return;
        }

        showAppointmentAlert('Thank you! A care officer will confirm shortly.', 'success');
        appointmentForm.reset();
        if (appointmentHoneypot) appointmentHoneypot.value = '';
    } catch (error) {
        console.error('Appointment submission error', error);
        showAppointmentAlert('Network error. Please try again soon.', 'danger');
    } finally {
        toggleAppointmentSubmitting(false);
    }
}

function initCarouselAnimations() {
    const carousel = document.getElementById('heroCarousel');
    if (!carousel) return;

    const carouselElement = new bootstrap.Carousel(carousel, {
        interval: 5000,
        wrap: true,
        pause: false
    });

    // Animate text on slide change
    carousel.addEventListener('slid.bs.carousel', function (event) {
        const activeItem = event.relatedTarget;
        const textContent = activeItem.querySelector('.hero-text-content');
        if (textContent) {
            // Reset animation
            textContent.style.animation = 'none';
            // Trigger reflow
            void textContent.offsetWidth;
            // Apply animation
            textContent.style.animation = 'fadeInUp 0.8s ease-out';
        }
    });

    // Animate initial slide
    const initialText = carousel.querySelector('.carousel-item.active .hero-text-content');
    if (initialText) {
        initialText.style.animation = 'fadeInUp 0.8s ease-out';
    }
}

function init() {
    if (form) {
        form.addEventListener('submit', submitForm);
        form.setAttribute('aria-describedby', 'formAlert');
    }

    if (appointmentForm) {
        appointmentForm.addEventListener('submit', submitAppointment);
        appointmentForm.setAttribute('aria-describedby', 'appointmentAlert');
    }

    if (scrollBtn) {
        scrollBtn.addEventListener('click', () => {
            document.getElementById('request-care').scrollIntoView({ behavior: 'smooth' });
        });
    }

    if (currentYear) {
        currentYear.textContent = new Date().getFullYear();
    }

    initCarouselAnimations();
}

document.addEventListener('DOMContentLoaded', init);

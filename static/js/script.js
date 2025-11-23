// competition date validation 
function initializeCompetitionForm() {
    const competitionForm = document.getElementById('competitionForm');

    if (competitionForm) {
        competitionForm.addEventListener('submit', function(e) {
            const  startDate = new Date(this.start_date.value);
            const endDate = new Date(this.end_date.value);
            const regDeadline = new Date(this.registration_deadline.value);
            const today = new Date();

            if (startDate >= endDate) {
                e.preventDefault();
                alert('End date must be after start date.');
                return;
            }

            if (regDeadline > startDate) {
                e.preventDefault();
                alert('Registration deadline must be before start date.');
                return;
            }

            if (regDeadline < today) {
                if (!confirm('Registration deadline is in the past. Continue anyway?')) {
                    e.preventDefault();
                    return;
                }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initializeCompetitionForm();
})

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', function() {
    console.log('TAMAULA Script loaded successfully');
    
    // Mobile menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }

    // Close mobile menu when clicking on a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (hamburger) hamburger.classList.remove('active');
            if (navMenu) navMenu.classList.remove('active');
        });
    });
});

// REMOVED: initializeMatchEvents(); // This was causing the error

// Club dropdown functionality
const localGovSelect = document.getElementById('local_government');
const clubSelect = document.getElementById('club');

if (localGovSelect && clubSelect) {
    // Initialize
    clubSelect.disabled = true;

    localGovSelect.addEventListener('change', function() {
        const selectedLG = this.value;

        // Clear and show loading
        clubSelect.innerHTML = '<option value="">Loading clubs...</option>';
        clubSelect.disabled = true;

        if (selectedLG) {
            fetch(`/get_clubs/${encodeURIComponent(selectedLG)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(clubs => {
                // Clear dropdown
                clubSelect.innerHTML = "";
                
                if (clubs && clubs.length > 0) {
                    // Add default option
                    const defaultOption = document.createElement('option');
                    defaultOption.value = "";
                    defaultOption.textContent = 'Select Club';
                    clubSelect.appendChild(defaultOption);

                    // Add each club
                    clubs.forEach((club) => {
                        const option = document.createElement('option');
                        option.value = club;
                        option.textContent = club;
                        clubSelect.appendChild(option);
                    });
                    
                    clubSelect.disabled = false;
                } else {
                    const noClubOption = document.createElement('option');
                    noClubOption.value = "";
                    noClubOption.textContent = 'No clubs found in this area';
                    clubSelect.appendChild(noClubOption);
                    clubSelect.disabled = true;
                }
            })
            .catch(error => {
                clubSelect.innerHTML = "";
                const errorOption = document.createElement('option');
                errorOption.value = "";
                errorOption.textContent = 'Error loading clubs';
                clubSelect.appendChild(errorOption);
                clubSelect.disabled = true;
            });
        } else {
            clubSelect.innerHTML = '<option value="">Select Local Government first</option>';
            clubSelect.disabled = true;
        }
    });
}

// Form validation
const forms = document.querySelectorAll('form');
forms.forEach(form => {

    if (form.id === 'AddEventForm') {
        return;
    }
    form.addEventListener('submit', function(e) {
        let isValid = true;
        const requiredFields = this.querySelectorAll('[required]');

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.style.borderColor = '#ef4444';
            } else {
                field.style.borderColor = '';
            }
        });

        if (!isValid) {
            e.preventDefault();
            alert("Please fill in all required fields.");
        }
    });
});


// Image preview
const fileInputs = document.querySelectorAll('input[type="file"]');
fileInputs.forEach(input => {
    input.addEventListener('change', function() {
        const previewId = this.getAttribute('data-preview');
        if (previewId) {
            const preview = document.getElementById(previewId);
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(this.files[0]);
            }
        }
    });
});

// Auto-hide flash messages
const flashMessages = document.querySelectorAll('.flash-message');
flashMessages.forEach(message => {
    setTimeout(() => {
        message.style.opacity = '0';
        setTimeout(() => {
            if (message.parentNode) {
                message.remove();
            }
        }, 500);
    }, 5000);
});
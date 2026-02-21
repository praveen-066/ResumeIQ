document.addEventListener('DOMContentLoaded', () => {

    // Initialize Particles if container exists
    if (document.getElementById('particles-js')) {
        initParticles();
    }

    // Check Page Context
    const uploadForm = document.getElementById('uploadForm');
    const resultPage = document.getElementById('scoreValue');

    if (uploadForm) {
        initUploadPage();
    } else if (resultPage) {
        initResultPage();
    }
});

/* --- PARTICLES CONFIG --- */
function initParticles() {
    particlesJS("particles-js", {
        "particles": {
            "number": { "value": 80, "density": { "enable": true, "value_area": 800 } },
            "color": { "value": "#ffffff" },
            "shape": { "type": "circle" },
            "opacity": { "value": 0.2, "random": true },
            "size": { "value": 3, "random": true },
            "line_linked": { "enable": true, "distance": 150, "color": "#ffffff", "opacity": 0.1, "width": 1 },
            "move": { "enable": true, "speed": 1, "direction": "none", "random": false, "straight": false, "out_mode": "out", "bounce": false }
        },
        "interactivity": {
            "detect_on": "canvas",
            "events": { "onhover": { "enable": true, "mode": "bubble" }, "onclick": { "enable": true, "mode": "push" }, "resize": true },
            "modes": { "bubble": { "distance": 200, "size": 4, "duration": 2, "opacity": 0.8 } }
        },
        "retina_detect": true
    });
}

/* --- UPLOAD PAGE LOGIC --- */
function initUploadPage() {
    // GSAP Entrance
    gsap.to(".gsap-hero", { duration: 1, opacity: 1, y: 0, ease: "power3.out", delay: 0.2 });
    gsap.to(".gsap-card", { duration: 1, opacity: 1, scale: 1, ease: "back.out(1.7)", delay: 0.5 });

    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('resumeFile');
    const fileNameDisplay = document.getElementById('fileName');
    const actionArea = document.getElementById('actionArea');
    const form = document.getElementById('uploadForm');

    // Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('border-neon', 'bg-white/10'));
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('border-neon', 'bg-white/10'));
    });

    dropZone.addEventListener('drop', (e) => {
        const file = e.dataTransfer.files[0];
        handleFileSelection(file);
    });

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFileSelection(file);
    });

    function handleFileSelection(file) {
        if (!file) return;

        // Update Input (if dropped)
        if (fileInput.files[0] !== file) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
        }

        // Visual Feedback
        fileNameDisplay.innerHTML = `<i class="fa-regular fa-file-pdf mr-2"></i>${file.name}`;
        fileNameDisplay.classList.remove('opacity-0', 'translate-y-2');
        dropZone.classList.add('border-neon');

        // Reveal Submit Button
        actionArea.style.maxHeight = "100px";
        actionArea.style.opacity = "1";
    }

    // Submit & Terminal Animation
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) return;

        // 1. Show Terminal
        const terminal = document.getElementById('terminalLoader');
        terminal.style.display = 'flex';

        // 2. Start API Request (Async)
        const formData = new FormData(form);
        const apiRequest = fetch('/upload', { method: 'POST', body: formData });

        // 3. Play Animation (Concurrent)
        await playTerminalAnimation();

        // 4. Handle Response
        try {
            const response = await apiRequest;

            // Check content type
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") === -1) {
                // Not JSON (likely HTML redirect to login)
                if (response.status === 401 || response.status === 403 || response.url.includes('/login')) {
                    alert('Session expired. Please log in again.');
                    window.location.href = '/auth/login';
                    return;
                }
                throw new Error("Received non-JSON response from server");
            }

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('resumeAnalysis', JSON.stringify(data));
                window.location.href = '/result';
            } else {
                alert(data.error || 'Upload failed');
                terminal.style.display = 'none';
            }
        } catch (error) {
            console.error('Upload Error:', error);
            alert('An error occurred during upload. Please check console.');
            terminal.style.display = 'none';
        }
    });
}

function playTerminalAnimation() {
    return new Promise((resolve) => {
        const linesContainer = document.getElementById('terminalLines');
        const progressBar = document.getElementById('progressBar');
        const tasks = [
            "Initializing secure environment...",
            "Reading document structure...",
            "Extracting entity data...",
            "Parsing employment history...",
            "Identifying skill keywords...",
            "Matching target role requirements...",
            "Calculating ATS compatibility...",
            "Compiling final report..."
        ];

        let delay = 0;
        const lineSpeed = 600; // ms per line

        tasks.forEach((task, index) => {
            setTimeout(() => {
                const p = document.createElement('div');
                p.className = 'terminal-line';
                p.innerHTML = `> ${task}`;
                linesContainer.appendChild(p);

                // Reveal line
                gsap.to(p, { opacity: 1, duration: 0.1 });

                // Update Progress
                const progress = ((index + 1) / tasks.length) * 100;
                gsap.to(progressBar, { width: `${progress}%`, duration: 0.5 });

                // Scroll to bottom
                linesContainer.scrollTop = linesContainer.scrollHeight;

            }, delay);
            delay += lineSpeed;
        });

        // Resolve after all animations + buffer
        setTimeout(resolve, delay + 1000);
    });
}

/* --- RESULT PAGE LOGIC --- */
function initResultPage() {
    let data;
    if (window.serverData) {
        data = window.serverData;
    } else {
        const dataString = localStorage.getItem('resumeAnalysis');
        if (!dataString) {
            window.location.href = '/';
            return;
        }
        data = JSON.parse(dataString);
    }

    // Populate Data
    document.getElementById('targetRoleDisplay').textContent = data.role;
    document.getElementById('scoreMessage').textContent = getScoreMessage(data.score);

    // Contact Info
    const contactList = document.getElementById('contactInfoList');
    contactList.innerHTML = [
        { label: 'Email', value: data.details.email, icon: 'fa-envelope' },
        { label: 'Phone', value: data.details.phone, icon: 'fa-phone' },
        // Add more fake fields for UI density if needed
        { label: 'Portfolio', value: data.details.projects ? 'Detected' : 'Missing', icon: 'fa-globe' }
    ].map(c => `
        <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5 hover:border-white/20 transition">
            <span class="text-gray-400 text-sm flex items-center"><i class="fa-solid ${c.icon} w-6 text-neon"></i> ${c.label}</span>
            <span class="font-medium text-sm ${c.value && c.value !== 'Missing' ? 'text-white' : 'text-red-400'}">${c.value || 'Not Found'}</span>
        </div>
    `).join('');

    // Skills
    renderTags('foundSkills', data.details.skills, 'bg-green-500/10 text-green-400 border border-green-500/20');
    renderTags('missingSkills', data.suggestions.missing_keywords, 'bg-red-500/10 text-red-400 border border-red-500/20');

    // Suggestions
    renderList('strengthsList', data.suggestions.strengths);
    renderList('improvementsList', [...data.suggestions.weaknesses, ...data.suggestions.improvements]);

    // Animate Score
    animateScore(data.score);

    // Render Chart
    if (data.breakdown) {
        renderModernChart(data.breakdown);
    }

    // GSAP Staggered Entrance
    gsap.from(".gsap-fade", { duration: 1, opacity: 0, y: -20, delay: 0.2 });
    gsap.from(".gsap-box", {
        duration: 0.8,
        opacity: 0,
        y: 30,
        stagger: 0.1,
        ease: "power2.out",
        delay: 0.4
    });
}

function getScoreMessage(score) {
    if (score >= 80) return "Excellent! Ready for applications.";
    if (score >= 60) return "Good, but needs optimization.";
    return "Needs significant improvement.";
}

function animateScore(score) {
    const display = document.getElementById('scoreValue');
    const circle = document.getElementById('scoreCircle');
    const radius = 45;
    const circumference = 2 * Math.PI * radius;

    // Set chart initial state
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    circle.style.strokeDashoffset = circumference;

    const offset = circumference - (score / 100) * circumference;

    // Animate Number
    let current = 0;
    const timer = setInterval(() => {
        if (current >= score) clearInterval(timer);
        else {
            current++;
            display.textContent = current;
        }
    }, 2000 / score); // 2 seconds total

    // Animate Stroke
    setTimeout(() => {
        circle.style.transition = "stroke-dashoffset 2s ease-in-out";
        circle.style.strokeDashoffset = offset;
    }, 500);
}

function renderTags(id, items, classes) {
    const container = document.getElementById(id);
    if (!items || !items.length) {
        container.innerHTML = '<span class="text-gray-600 italic text-xs">None detected</span>';
    } else {
        container.innerHTML = items.map(item => `<span class="px-3 py-1 rounded-full text-xs font-medium ${classes}">${item}</span>`).join('');
    }
}

function renderList(id, items) {
    const container = document.getElementById(id);
    if (!items || !items.length) {
        container.innerHTML = '<li class="text-gray-600 italic">None found</li>';
    } else {
        container.innerHTML = items.map(item => `<li class="flex items-start"><i class="fa-solid fa-angle-right text-white/30 mr-2 mt-1 underline-none"></i><span>${item}</span></li>`).join('');
    }
}

function renderModernChart(breakdown) {
    const ctx = document.getElementById('scoreChart').getContext('2d');

    // Premium Dark Chart Config
    Chart.defaults.color = '#6b7280';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';

    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: Object.keys(breakdown),
            datasets: [{
                label: 'Your Resume',
                data: Object.values(breakdown),
                backgroundColor: 'rgba(0, 243, 255, 0.2)',
                borderColor: '#00f3ff',
                borderWidth: 2,
                pointBackgroundColor: '#00f3ff',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#00f3ff'
            }, {
                label: 'Ideal Candidate',
                data: [5, 20, 15, 15, 10, 10, 25],
                backgroundColor: 'transparent',
                borderColor: 'rgba(189, 0, 255, 0.3)',
                borderWidth: 1,
                borderDash: [4, 4],
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    pointLabels: {
                        color: '#fff',
                        font: { size: 11, family: "'Outfit', sans-serif" }
                    },
                    suggestedMin: 0,
                    suggestedMax: 25,
                    ticks: { display: false, backdropColor: 'transparent' }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#fff', usePointStyle: true, boxWidth: 6 }
                }
            }
        }
    });
}

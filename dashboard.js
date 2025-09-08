let candidates = [];
let filteredCandidates = [];
let selectedCandidate = null;
let charts = {};
let resumePaths = {};
let isPrivacyMode = false;

// Privacy toggle functionality
function togglePrivacy() {
    isPrivacyMode = !isPrivacyMode;
    const button = document.getElementById('privacy-toggle');
    const icon = document.getElementById('privacy-icon');
    const text = document.getElementById('privacy-text');
    
    if (isPrivacyMode) {
        button.classList.add('active');
        icon.textContent = '🔓';
        text.textContent = 'Unhide';
    } else {
        button.classList.remove('active');
        icon.textContent = '🔒';
        text.textContent = 'Anonymize';
    }
    
    updateCandidatesList();
}

// Mask sensitive information
function maskText(text, type) {
    if (!isPrivacyMode) return text;
    
    if (type === 'name') {
        return '█'.repeat(Math.max(8, text.length));
    } else if (type === 'email') {
        const [local, domain] = text.split('@');
        if (local && domain) {
            return local.charAt(0) + '█'.repeat(Math.max(3, local.length - 1)) + '@' + domain.charAt(0) + '█'.repeat(Math.max(3, domain.length - 1));
        }
        return '█'.repeat(Math.max(8, text.length));
    } else if (type === 'accomplishment') {
        const words = text.split(' ');
        if (words.length > 1) {
            return words[0] + ' ' + words.slice(1).map(word => '█'.repeat(word.length)).join(' ');
        }
        return '█'.repeat(Math.max(8, text.length));
    } else if (type === 'companies') {
        const companies = text.split(',').map(c => c.trim());
        if (companies.length > 0) {
            return companies.map(company => '█'.repeat(Math.max(4, company.length))).join(', ');
        }
        return text;
    }
    return text;
}


// Load and parse CSV data
async function loadCandidates() {
    try {
        // Load resume paths
        const resumeResponse = await fetch('resume_paths.json');
        resumePaths = await resumeResponse.json();
        
        // Get CSV filename from URL parameter or default
        const urlParams = new URLSearchParams(window.location.search);
        const csvFile = urlParams.get('csv') || 'candidates.csv';
        
        // Show which CSV file is being loaded
        console.log('Loading CSV file:', csvFile);
        document.title = `Recruiting Dashboard - ${csvFile}`;
        
        // Load candidate data
        const response = await fetch(csvFile);
        const csvText = await response.text();
        candidates = parseCSV(csvText);
        filteredCandidates = [...candidates];
        
        updateAnalytics();
        updateCharts();
        updateCandidatesList();
        updateFilters();
    } catch (error) {
        console.error('Error loading candidates:', error);
        document.getElementById('candidates-list').innerHTML = 
            '<div class="error">Error loading candidate data. Please check if test.csv exists.</div>';
    }
}

// Parse CSV data with proper quoted field handling
function parseCSV(csvText) {
    const lines = csvText.split('\n');
    const headers = parseCSVLine(lines[0]);
    
    return lines.slice(1)
        .filter(line => line.trim())
        .map(line => {
            const values = parseCSVLine(line);
            const candidate = {};
            headers.forEach((header, index) => {
                candidate[header] = values[index] || '';
            });
            
            // Convert numeric fields
            const numericFields = [
                'programming_experience_years', 'ai_experience_years', 'college_education_years',
                'university_tier', 'overall_world_ranking', 'cs_world_ranking', 'bachelors_gpa', 'masters_gpa',
                'company_tier', 'javascript_skill_level', 'python_skill_level', 'cloud_skill_level', 'llm_skill_level',
                'cs_internships', 'cloud_experience_years', 'llm_experience_years', 'react_strength', 'typescript_strength',
                'nextjs_strength', 'api_design_strength', 'tailwind_strength', 'git_strength', 'agile_strength',
                'startup_experience_strength', 'open_source_strength', 'leadership_strength', 'algorithms_strength',
                'system_design_strength', 'academic_strength', 'cs_strength', 'industry_strength', 'fullstack_strength',
                'opensource_strength', 'accomplishments_strength', 'overall_score'
            ];
            
            numericFields.forEach(field => {
                if (candidate[field] && !isNaN(candidate[field])) {
                    candidate[field] = parseFloat(candidate[field]);
                } else {
                    candidate[field] = 0;
                }
            });
            
            return candidate;
        })
        .sort((a, b) => b.overall_score - a.overall_score);
}

// Parse a single CSV line, handling quoted fields properly
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        
        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                // Escaped quote
                current += '"';
                i++; // Skip next quote
            } else {
                // Toggle quote state
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            // End of field
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    
    // Add the last field
    result.push(current.trim());
    return result;
}

// Update analytics
function updateAnalytics() {
    const totalCandidates = candidates.length;
    const avgScore = candidates.reduce((sum, c) => sum + c.overall_score, 0) / totalCandidates;
    const topTier = candidates.filter(c => c.university_tier <= 2).length;
    const avgExperience = candidates.reduce((sum, c) => sum + c.programming_experience_years, 0) / totalCandidates;

    document.getElementById('total-candidates').textContent = totalCandidates;
    document.getElementById('avg-score').textContent = avgScore.toFixed(1);
    document.getElementById('top-tier').textContent = topTier;
    document.getElementById('experience-level').textContent = avgExperience.toFixed(1);
}

// Update charts
function updateCharts() {
    updateUniversityChart();
    updateExperienceChart();
    updateScoreChart();
    updateJobLevelChart();
}

// University tier and CS ranking mapping
const universityTiers = {
    // Tier 1 (Top 10)
    'Stanford University': 1, 'MIT': 1, 'Harvard University': 1, 'UC Berkeley': 1, 'Carnegie Mellon University': 1,
    'University of Illinois Urbana-Champaign': 1, 'Georgia Institute of Technology': 1, 'University of Michigan': 1,
    'Cornell University': 1, 'University of Washington': 1, 'Princeton University': 1, 'Yale University': 1,
    'Columbia University': 1, 'University of Pennsylvania': 1, 'University of California, Los Angeles': 1,
    'University of California, San Diego': 1, 'University of Texas at Austin': 1, 'University of Wisconsin-Madison': 1,
    'University of Maryland': 1, 'Purdue University': 1, 'University of Southern California': 1,
    'New York University': 1, 'University of California, Irvine': 1, 'University of Virginia': 1,
    'University of North Carolina at Chapel Hill': 1, 'University of Minnesota': 1, 'Ohio State University': 1,
    'University of Florida': 1, 'University of Pittsburgh': 1, 'University of Arizona': 1,
    'University of California, Davis': 1, 'University of California, Santa Barbara': 1, 'University of Rochester': 1,
    'University of Notre Dame': 1, 'Duke University': 1, 'Northwestern University': 1, 'Rice University': 1,
    'University of Chicago': 1, 'Johns Hopkins University': 1, 'Brown University': 1, 'Dartmouth College': 1,
    'Vanderbilt University': 1, 'Emory University': 1, 'Georgetown University': 1, 'Tufts University': 1,
    'Wake Forest University': 1, 'Boston College': 1, 'Brandeis University': 1, 'Case Western Reserve University': 1,
    'Lehigh University': 1, 'Northeastern University': 1, 'Pepperdine University': 1, 'Rensselaer Polytechnic Institute': 1,
    'University of Miami': 1, 'Villanova University': 1, 'Worcester Polytechnic Institute': 1,
    
    // Tier 2 (Good)
    'Arizona State University': 2, 'Boston University': 2, 'Clemson University': 2, 'Colorado State University': 2,
    'DePaul University': 2, 'Drexel University': 2, 'Florida State University': 2, 'George Mason University': 2,
    'George Washington University': 2, 'Indiana University': 2, 'Iowa State University': 2, 'Kansas State University': 2,
    'Louisiana State University': 2, 'Michigan State University': 2, 'Mississippi State University': 2,
    'Missouri University of Science and Technology': 2, 'Montana State University': 2, 'New Jersey Institute of Technology': 2,
    'North Carolina State University': 2, 'Oklahoma State University': 2, 'Oregon State University': 2,
    'Penn State University': 2, 'Rutgers University': 2, 'San Diego State University': 2, 'San Jose State University': 2,
    'Stony Brook University': 2, 'Syracuse University': 2, 'Temple University': 2, 'Texas A&M University': 2,
    'University of Alabama': 2, 'University of Arkansas': 2, 'University of California, Riverside': 2,
    'University of Central Florida': 2, 'University of Cincinnati': 2, 'University of Colorado Boulder': 2,
    'University of Connecticut': 2, 'University of Delaware': 2, 'University of Georgia': 2, 'University of Houston': 2,
    'University of Iowa': 2, 'University of Kansas': 2, 'University of Kentucky': 2, 'University of Louisville': 2,
    'University of Massachusetts': 2, 'University of Missouri': 2, 'University of Nebraska': 2, 'University of Nevada': 2,
    'University of New Hampshire': 2, 'University of New Mexico': 2, 'University of Oklahoma': 2, 'University of Oregon': 2,
    'University of Rhode Island': 2, 'University of South Carolina': 2, 'University of South Florida': 2,
    'University of Tennessee': 2, 'University of Utah': 2, 'University of Vermont': 2, 'University of Wyoming': 2,
    'Virginia Tech': 2, 'Washington State University': 2, 'Wayne State University': 2, 'West Virginia University': 2,
    
    // Tier 3 (Other)
    'Unknown': 3, 'Other': 3
};

// CS Rankings (US News 2024)
const universityCSRankings = {
    'MIT': 1, 'Stanford University': 1, 'UC Berkeley': 1, 'Carnegie Mellon University': 1,
    'University of Illinois Urbana-Champaign': 5, 'Georgia Institute of Technology': 5, 'University of Michigan': 7,
    'Cornell University': 7, 'University of Washington': 9, 'Princeton University': 9, 'University of Texas at Austin': 9,
    'University of California, San Diego': 12, 'University of Wisconsin-Madison': 13, 'University of Maryland': 14,
    'University of California, Los Angeles': 15, 'Columbia University': 15, 'University of Pennsylvania': 17,
    'Purdue University': 18, 'University of Southern California': 19, 'University of California, Irvine': 20,
    'University of Virginia': 21, 'University of North Carolina at Chapel Hill': 22, 'University of Minnesota': 23,
    'Ohio State University': 24, 'University of Florida': 25, 'University of Pittsburgh': 26, 'University of Arizona': 27,
    'University of California, Davis': 28, 'University of California, Santa Barbara': 29, 'University of Rochester': 30,
    'University of Notre Dame': 31, 'Duke University': 32, 'Northwestern University': 33, 'Rice University': 34,
    'University of Chicago': 35, 'Johns Hopkins University': 36, 'Brown University': 37, 'Dartmouth College': 38,
    'Vanderbilt University': 39, 'Emory University': 40, 'Georgetown University': 41, 'Tufts University': 42,
    'Wake Forest University': 43, 'Boston College': 44, 'Brandeis University': 45, 'Case Western Reserve University': 46,
    'Lehigh University': 47, 'Northeastern University': 48, 'Pepperdine University': 49, 'Rensselaer Polytechnic Institute': 50,
    'University of Miami': 51, 'Villanova University': 52, 'Worcester Polytechnic Institute': 53,
    'Arizona State University': 54, 'Boston University': 55, 'Clemson University': 56, 'Colorado State University': 57,
    'DePaul University': 58, 'Drexel University': 59, 'Florida State University': 60, 'George Mason University': 61,
    'George Washington University': 62, 'Indiana University': 63, 'Iowa State University': 64, 'Kansas State University': 65,
    'Louisiana State University': 66, 'Michigan State University': 67, 'Mississippi State University': 68,
    'Missouri University of Science and Technology': 69, 'Montana State University': 70, 'New Jersey Institute of Technology': 71,
    'North Carolina State University': 72, 'Oklahoma State University': 73, 'Oregon State University': 74,
    'Penn State University': 75, 'Rutgers University': 76, 'San Diego State University': 77, 'San Jose State University': 78,
    'Stony Brook University': 79, 'Syracuse University': 80, 'Temple University': 81, 'Texas A&M University': 82,
    'University of Alabama': 83, 'University of Arkansas': 84, 'University of California, Riverside': 85,
    'University of Central Florida': 86, 'University of Cincinnati': 87, 'University of Colorado Boulder': 88,
    'University of Connecticut': 89, 'University of Delaware': 90, 'University of Georgia': 91, 'University of Houston': 92,
    'University of Iowa': 93, 'University of Kansas': 94, 'University of Kentucky': 95, 'University of Louisville': 96,
    'University of Massachusetts': 97, 'University of Missouri': 98, 'University of Nebraska': 99, 'University of Nevada': 100,
    'University of New Hampshire': 101, 'University of New Mexico': 102, 'University of Oklahoma': 103, 'University of Oregon': 104,
    'University of Rhode Island': 105, 'University of South Carolina': 106, 'University of South Florida': 107,
    'University of Tennessee': 108, 'University of Utah': 109, 'University of Vermont': 110, 'University of Wyoming': 111,
    'Virginia Tech': 112, 'Washington State University': 113, 'Wayne State University': 114, 'West Virginia University': 115
};

        function getUniversityInfo(universityName) {
    const tier = universityTiers[universityName] || 3;
    const ranking = universityCSRankings[universityName];
    const tierNames = { 1: 'T1', 2: 'T2', 3: 'T3' };
    
    if (ranking) {
        return `(${ranking}, ${tierNames[tier]})`;
    } else {
        return `(${tierNames[tier]})`;
    }
}

function updateUniversityChart() {
    const universityCounts = {};
    candidates.forEach(candidate => {
        const university = candidate.bachelors_university || candidate.graduate_university || 'Unknown';
        universityCounts[university] = (universityCounts[university] || 0) + 1;
    });

    // Sort universities by tier first, then by count within each tier
    const sortedUniversities = Object.entries(universityCounts)
        .sort((a, b) => {
            const tierA = universityTiers[a[0]] || 3;
            const tierB = universityTiers[b[0]] || 3;
            
            // First sort by tier (1, 2, 3)
            if (tierA !== tierB) {
                return tierA - tierB;
            }
            
            // Within same tier, sort by count (descending)
            return b[1] - a[1];
        })
        .slice(0, 70); // Show top 70 universities

    const tierColors = {
        1: 'rgba(40, 167, 69, 0.8)',   // Green for Tier 1
        2: 'rgba(255, 193, 7, 0.8)',   // Yellow for Tier 2
        3: 'rgba(108, 117, 125, 0.8)'  // Gray for Tier 3
    };

    const ctx = document.getElementById('universityChart').getContext('2d');
    if (charts.university) charts.university.destroy();
    
    charts.university = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedUniversities.map(u => u[0]),
            datasets: [{
                label: 'Candidates',
                data: sortedUniversities.map(u => u[1]),
                backgroundColor: sortedUniversities.map(u => {
                    const tier = universityTiers[u[0]] || 3;
                    return tierColors[tier];
                }),
                borderColor: sortedUniversities.map(u => {
                    const tier = universityTiers[u[0]] || 3;
                    return tierColors[tier].replace('0.8', '1');
                }),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        generateLabels: function(chart) {
                            return [
                                { text: 'Tier 1 (Top Universities)', fillStyle: tierColors[1], strokeStyle: tierColors[1] },
                                { text: 'Tier 2 (Good Universities)', fillStyle: tierColors[2], strokeStyle: tierColors[2] },
                                { text: 'Tier 3 (Other)', fillStyle: tierColors[3], strokeStyle: tierColors[3] }
                            ];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 70,
                        font: {
                            size: 9
                        }
                    }
                }
            }
        }
    });
}

function updateExperienceChart() {
    const experienceRanges = {
        '0-1 years': 0,
        '2-3 years': 0,
        '4-5 years': 0,
        '6+ years': 0
    };

    candidates.forEach(candidate => {
        const exp = candidate.programming_experience_years;
        if (exp <= 1) experienceRanges['0-1 years']++;
        else if (exp <= 3) experienceRanges['2-3 years']++;
        else if (exp <= 5) experienceRanges['4-5 years']++;
        else experienceRanges['6+ years']++;
    });

    const ctx = document.getElementById('experienceChart').getContext('2d');
    if (charts.experience) charts.experience.destroy();
    
    charts.experience = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(experienceRanges),
            datasets: [{
                data: Object.values(experienceRanges),
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function updateScoreChart() {
    const scoreRanges = {
        '3.0-4.0': 0,
        '4.1-5.0': 0,
        '5.1-6.0': 0,
        '6.1-7.0': 0,
        '7.1-8.0': 0,
        '8.1+': 0
    };

    candidates.forEach(candidate => {
        const score = candidate.overall_score;
        if (score <= 4.0) scoreRanges['3.0-4.0']++;
        else if (score <= 5.0) scoreRanges['4.1-5.0']++;
        else if (score <= 6.0) scoreRanges['5.1-6.0']++;
        else if (score <= 7.0) scoreRanges['6.1-7.0']++;
        else if (score <= 8.0) scoreRanges['7.1-8.0']++;
        else scoreRanges['8.1+']++;
    });

    const ctx = document.getElementById('scoreChart').getContext('2d');
    if (charts.score) charts.score.destroy();
    
    charts.score = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(scoreRanges),
            datasets: [{
                label: 'Candidates',
                data: Object.values(scoreRanges),
                backgroundColor: 'rgba(118, 75, 162, 0.8)',
                borderColor: 'rgba(118, 75, 162, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true
                    }
                }
            }
        }
    });
}

function updateJobLevelChart() {
    const jobLevelCounts = {};
    candidates.forEach(candidate => {
        const level = candidate.estimated_job_level || 'Unknown';
        jobLevelCounts[level] = (jobLevelCounts[level] || 0) + 1;
    });

    const ctx = document.getElementById('jobLevelChart').getContext('2d');
    if (charts.jobLevel) charts.jobLevel.destroy();
    
    charts.jobLevel = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(jobLevelCounts),
            datasets: [{
                data: Object.values(jobLevelCounts),
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)',
                    'rgba(40, 167, 69, 0.8)',
                    'rgba(23, 162, 184, 0.8)'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Update candidates list
function updateCandidatesList() {
    const container = document.getElementById('candidates-list');
    
    if (filteredCandidates.length === 0) {
        container.innerHTML = '<div class="loading">No candidates match your filters</div>';
        return;
    }

    container.innerHTML = filteredCandidates.map(candidate => {
        const resumePath = resumePaths[candidate.resume_filename] || '';
        const resumeLink = resumePath ? `<a href="${resumePath}" target="_blank" class="candidate-link" onclick="event.stopPropagation()">Resume</a>` : '';
        const topAccomplishment = candidate.accomplishment_1 || candidate.accomplishment_2 || candidate.accomplishment_3 || '';
        
        // Build university information
        let universityDisplay = '';
        if (candidate.graduate_university && candidate.bachelors_university) {
            const bachelorsInfo = getUniversityInfo(candidate.bachelors_university);
            const graduateInfo = getUniversityInfo(candidate.graduate_university);
            universityDisplay = `${candidate.bachelors_university} ${bachelorsInfo} → ${candidate.graduate_university} ${graduateInfo}`;
        } else if (candidate.graduate_university) {
            const graduateInfo = getUniversityInfo(candidate.graduate_university);
            universityDisplay = `${candidate.graduate_university} ${graduateInfo}`;
        } else if (candidate.bachelors_university) {
            const bachelorsInfo = getUniversityInfo(candidate.bachelors_university);
            universityDisplay = `${candidate.bachelors_university} ${bachelorsInfo}`;
        } else {
            universityDisplay = 'University not specified';
        }
        
        // Add education years and degree
        const educationYears = candidate.college_education_years || 0;
        const highestDegree = candidate.highest_degree || '';
        const educationInfo = `(${educationYears}y, ${highestDegree})`;
        
        // Add experience information
        const programmingYears = candidate.programming_experience_years || 0;
        const aiYears = candidate.ai_experience_years || 0;
        const experienceInfo = `(${programmingYears}y prog, ${aiYears}y AI)`;
        
        // Extract companies from work experience
        const companiesText = candidate.companies_worked || 'No work experience';
        
        return `
            <div class="candidate-card ${selectedCandidate === candidate ? 'selected' : ''}" 
                 onclick="selectCandidate('${candidate.candidate_name}')">
                <!-- Line 1: Name, email, universities with ranking/tier, education info, links, overall score -->
                <div class="candidate-line">
                    <div>
                        <span class="candidate-name">${maskText(candidate.candidate_name, 'name')}</span>
                        <span class="candidate-email">${maskText(candidate.email, 'email')}</span>
                        <span class="candidate-university">${universityDisplay} ${educationInfo}</span>
                    </div>
                    <div class="candidate-scores-container">
                        <div class="candidate-links">
                            ${resumeLink}
                            ${candidate.github_link ? `<a href="${candidate.github_link.startsWith('http') ? candidate.github_link : 'https://' + candidate.github_link}" target="_blank" class="candidate-link" onclick="event.stopPropagation()">GitHub</a>` : ''}
                            ${candidate.linkedin_link ? `<a href="${candidate.linkedin_link.startsWith('http') ? candidate.linkedin_link : 'https://' + candidate.linkedin_link}" target="_blank" class="candidate-link" onclick="event.stopPropagation()">LinkedIn</a>` : ''}
                        </div>
                        <span class="candidate-score">${candidate.overall_score.toFixed(1)}</span>
                    </div>
                </div>
                
                <!-- Line 2: Companies, experience info, and aggregate scores -->
                <div class="candidate-line">
                    <div class="candidate-companies">
                        <span class="company-text">${maskText(companiesText, 'companies')}</span>
                        <span class="experience-info">${experienceInfo}</span>
                    </div>
                    <div class="candidate-scores-container">
                        <span class="score-item">CS:${candidate.cs_strength}</span>
                        <span class="score-item">Ind:${candidate.industry_strength}</span>
                        <span class="score-item">FS:${candidate.fullstack_strength}</span>
                        <span class="score-item">OS:${candidate.opensource_strength}</span>
                        <span class="score-item">Acc:${candidate.accomplishments_strength}</span>
                        <span class="score-item">Acad:${candidate.academic_strength}</span>
                    </div>
                </div>
                
                <!-- Line 3: Top accomplishment and job level -->
                ${topAccomplishment ? `<div class="candidate-line">
                    <div class="candidate-accomplishment">${maskText(topAccomplishment, 'accomplishment')}</div>
                    <div class="candidate-job-level">${candidate.estimated_job_level}</div>
                </div>` : `<div class="candidate-line">
                    <div></div>
                    <div class="candidate-job-level">${candidate.estimated_job_level}</div>
                </div>`}
            </div>
        `;
    }).join('');
}

// Update filters
function updateFilters() {
    const universities = [...new Set(candidates.map(c => c.bachelors_university || c.graduate_university).filter(Boolean))].sort();
    const universityFilter = document.getElementById('university-filter');
    
    universityFilter.innerHTML = '<option value="">All Universities</option>' +
        universities.map(u => `<option value="${u}">${u}</option>`).join('');
}



// Select candidate
function selectCandidate(candidateName) {
    selectedCandidate = candidates.find(c => c.candidate_name === candidateName);
    updateCandidatesList();
    updateDetailPanel();
}



// Update detail panel
function updateDetailPanel() {
    if (!selectedCandidate) {
        document.getElementById('detail-panel').innerHTML = `
            <div class="no-selection">
                <h3>Select a candidate to view details</h3>
                <p>Click on any candidate card to see their full profile and scores</p>
            </div>
        `;
        return;
    }

    const c = selectedCandidate;
    const resumePath = resumePaths[c.resume_filename] || '';
    const resumeLink = resumePath ? `<a href="${resumePath}" target="_blank" class="detail-link">View Resume</a>` : '';
    document.getElementById('detail-panel').innerHTML = `
        <div class="detail-header">
            <div class="detail-name">${maskText(c.candidate_name, 'name')}</div>
            <div class="detail-score">Overall Score: ${c.overall_score.toFixed(1)}</div>
        </div>

        <div class="detail-section">
            <h3>Contact Information</h3>
            <div class="detail-item">
                <span class="detail-label">Email:</span>
                <span class="detail-value">${maskText(c.email, 'email')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Location:</span>
                <span class="detail-value">${c.city}, ${c.country}</span>
            </div>
            <div class="detail-links">
                ${resumeLink}
                ${c.github_link ? `<a href="${c.github_link.startsWith('http') ? c.github_link : 'https://' + c.github_link}" target="_blank" class="detail-link">GitHub Profile</a>` : ''}
                ${c.linkedin_link ? `<a href="${c.linkedin_link.startsWith('http') ? c.linkedin_link : 'https://' + c.linkedin_link}" target="_blank" class="detail-link">LinkedIn Profile</a>` : ''}
            </div>

        </div>

        <div class="detail-section">
            <h3>Education</h3>
            <div class="detail-item">
                <span class="detail-label">Highest Degree:</span>
                <span class="detail-value">${c.highest_degree}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Bachelor's University:</span>
                <span class="detail-value">${c.bachelors_university || 'Not specified'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Graduate University:</span>
                <span class="detail-value">${c.graduate_university || 'Not specified'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">University Tier:</span>
                <span class="detail-value">${c.university_tier}/5</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Bachelor's GPA:</span>
                <span class="detail-value">${c.bachelors_gpa > 0 ? c.bachelors_gpa : 'Not specified'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Master's GPA:</span>
                <span class="detail-value">${c.masters_gpa > 0 ? c.masters_gpa : 'Not specified'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Experience</h3>
            <div class="detail-item">
                <span class="detail-label">Job Level:</span>
                <span class="detail-value">${c.estimated_job_level}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Programming Experience:</span>
                <span class="detail-value">${c.programming_experience_years} years</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">AI Experience:</span>
                <span class="detail-value">${c.ai_experience_years} years</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Companies:</span>
                <span class="detail-value">${maskText(c.companies_worked || 'Not specified', 'companies')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Company Tier:</span>
                <span class="detail-value">${c.company_tier}/5</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Technical Skills</h3>
            <div class="detail-item">
                <span class="detail-label">JavaScript/TypeScript:</span>
                <span class="detail-value">${c.javascript_skill_level}/5</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Python:</span>
                <span class="detail-value">${c.python_skill_level}/5</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Cloud:</span>
                <span class="detail-value">${c.cloud_skill_level}/5</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">LLM/NLP:</span>
                <span class="detail-value">${c.llm_skill_level}/5</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">React:</span>
                <span class="detail-value">${c.react_strength}/5</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">AWS Services:</span>
                <span class="detail-value">${c.aws_services_experience || 'Not specified'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Databases:</span>
                <span class="detail-value">${c.database_technologies || 'Not specified'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Aggregate Scores</h3>
            <div class="detail-item">
                <span class="detail-label">Academic Strength:</span>
                <span class="detail-value">${c.academic_strength}/10</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">CS Fundamentals:</span>
                <span class="detail-value">${c.cs_strength}/10</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Industry Experience:</span>
                <span class="detail-value">${c.industry_strength}/10</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Full-stack Development:</span>
                <span class="detail-value">${c.fullstack_strength}/10</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Open Source:</span>
                <span class="detail-value">${c.opensource_strength}/10</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Accomplishments:</span>
                <span class="detail-value">${c.accomplishments_strength}/10</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Top Accomplishments</h3>
            <div class="accomplishments">
                ${c.accomplishment_1 ? `<div class="accomplishment">${maskText(c.accomplishment_1, 'accomplishment')}</div>` : ''}
                ${c.accomplishment_2 ? `<div class="accomplishment">${maskText(c.accomplishment_2, 'accomplishment')}</div>` : ''}
                ${c.accomplishment_3 ? `<div class="accomplishment">${maskText(c.accomplishment_3, 'accomplishment')}</div>` : ''}
            </div>
        </div>
    `;
}

// Filter candidates
function filterCandidates() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const jobLevel = document.getElementById('job-level-filter').value;
    const university = document.getElementById('university-filter').value;

    filteredCandidates = candidates.filter(candidate => {
        const matchesSearch = !searchTerm || 
            candidate.candidate_name.toLowerCase().includes(searchTerm) ||
            candidate.email.toLowerCase().includes(searchTerm) ||
            (candidate.bachelors_university && candidate.bachelors_university.toLowerCase().includes(searchTerm)) ||
            (candidate.graduate_university && candidate.graduate_university.toLowerCase().includes(searchTerm));

        const matchesJobLevel = !jobLevel || candidate.estimated_job_level === jobLevel;
        
        const matchesUniversity = !university || 
            candidate.bachelors_university === university || 
            candidate.graduate_university === university;

        return matchesSearch && matchesJobLevel && matchesUniversity;
    });

    updateCandidatesList();
}

// Event listeners
document.getElementById('search-input').addEventListener('input', filterCandidates);
document.getElementById('job-level-filter').addEventListener('change', filterCandidates);
document.getElementById('university-filter').addEventListener('change', filterCandidates);
document.getElementById('privacy-toggle').addEventListener('click', togglePrivacy);

// Initialize dashboard
loadCandidates();
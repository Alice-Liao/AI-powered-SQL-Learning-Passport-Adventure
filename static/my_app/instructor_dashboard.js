document.addEventListener('DOMContentLoaded', function() {
    // Initialize search functionality
    const searchInput = document.getElementById('studentSearch');
    const studentTable = document.getElementById('studentTable');
    const filterSelect = document.getElementById('progressFilter');

    if (searchInput && studentTable) {
        searchInput.addEventListener('input', function() {
            filterStudents();
        });
    }

    if (filterSelect && studentTable) {
        filterSelect.addEventListener('change', function() {
            filterStudents();
        });
    }

    // Function to filter students based on search and progress filter
    function filterStudents() {
        const searchTerm = searchInput.value.toLowerCase();
        const filterValue = filterSelect.value;
        const rows = studentTable.getElementsByTagName('tr');

        for (let i = 1; i < rows.length; i++) { // Start from 1 to skip header
            const row = rows[i];
            const name = row.cells[0].textContent.toLowerCase();
            const email = row.cells[1].textContent.toLowerCase();
            const progress = parseFloat(row.cells[4].textContent);

            const matchesSearch = name.includes(searchTerm) || email.includes(searchTerm);
            let matchesFilter = true;

            if (filterValue !== 'all') {
                const range = filterValue.split('-');
                const min = parseFloat(range[0]);
                const max = parseFloat(range[1]);
                matchesFilter = progress >= min && progress <= max;
            }

            row.style.display = matchesSearch && matchesFilter ? '' : 'none';
        }
    }

    // Function to send message to student
    window.sendMessage = function(studentId) {
        // TODO: Implement message sending functionality
        console.log('Sending message to student:', studentId);
        // This would typically open a modal or redirect to a messaging interface
    };

    // Function to view student details
    window.viewStudentDetails = function(studentId) {
        // TODO: Implement student details view
        console.log('Viewing details for student:', studentId);
        // This would typically redirect to a student details page
    };

    // Initialize progress bars
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const progress = parseFloat(bar.dataset.progress);
        const fill = bar.querySelector('.progress-fill');
        if (fill) {
            fill.style.width = `${progress}%`;
        }
    });

    // Add event listeners for task analytics
    const taskCards = document.querySelectorAll('.task-stat-card');
    taskCards.forEach(card => {
        card.addEventListener('click', function() {
            // TODO: Implement task details view
            console.log('Viewing task details:', this.dataset.taskId);
        });
    });
}); 
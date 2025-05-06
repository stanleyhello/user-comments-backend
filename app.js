document.addEventListener('DOMContentLoaded', () => {
    const commentForm = document.getElementById('commentForm');
    const refreshSummaryBtn = document.getElementById('refreshSummary');
    const summaryText = document.getElementById('summaryText');

    commentForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const companyInput = document.getElementById('companyInput');
        const commentInput = document.getElementById('commentInput');

        try {
            const response = await fetch('/submit_comment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company: companyInput.value,
                    comment: commentInput.value
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                alert('Comment submitted successfully!');
                companyInput.value = '';
                commentInput.value = '';
            } else {
                alert('Error submitting comment: ' + result.message);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while submitting the comment.');
        }
    });

    async function fetchSummary() {
        try {
            const response = await fetch('/get_summary');
            const result = await response.json();
            
            if (result.status === 'success') {
                summaryText.textContent = result.summary || 'No summary available.';
            } else {
                summaryText.textContent = 'Error fetching summary: ' + result.message;
            }
        } catch (error) {
            console.error('Error:', error);
            summaryText.textContent = 'An error occurred while fetching the summary.';
        }
    }

    // Initial summary fetch
    fetchSummary();

    // Refresh summary button
    refreshSummaryBtn.addEventListener('click', fetchSummary);
});

/**
 * ABRS Loader - Loading spinner for ABRS import operations
 */

/**
 * Show loading spinner for ABRS data import
 * @param {string} type - Type of import: 'serial' or 'date'
 * @param {object} data - Data to display (serialNumber or fromDate/toDate)
 */
function showAbrsLoader(type, data) {
  let detailsHtml = '';
  
  if (type === 'serial') {
    detailsHtml = `
      <p style="font-size: 0.9rem; color: #94a3b8; margin-top: 10px;">
        Serial Number: <strong>${data.serialNumber}</strong>
      </p>
    `;
  } else if (type === 'date') {
    detailsHtml = `
      <p style="font-size: 0.9rem; color: #94a3b8; margin-top: 10px;">
        From: <strong>${data.fromDate}</strong> To: <strong>${data.toDate}</strong>
      </p>
    `;
  }
  
  Swal.fire({
    title: 'Please Wait...',
    html: `
      <div style="text-align: center; padding: 20px;">
        <p style="font-size: 1rem; color: #64748b; margin-top: 15px;">
          <i class="fas fa-database me-2"></i>Fetching data from ABRS database...
        </p>
        ${detailsHtml}
      </div>
    `,
    allowOutsideClick: false,
    allowEscapeKey: false,
    showConfirmButton: false,
    didOpen: () => {
      Swal.showLoading(); // This shows SweetAlert's built-in spinner
    }
  });
}

/**
 * Close the ABRS loader
 */
function closeAbrsLoader() {
  Swal.close();
}

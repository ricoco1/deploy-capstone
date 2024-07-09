function printOrder(name, address, phone, roomType, checkIn, checkOut, nights, amount, status, kode_booking) {
    var { jsPDF } = window.jspdf;
    var doc = new jsPDF();
    
    // Header
    doc.setFontSize(20);
    doc.setFont("helvetica", "bold");
    doc.text("HOTEL TELAGA MAS", 105, 15, null, null, "center");
    
    doc.setFontSize(12);
    doc.setFont("helvetica", "normal");
    doc.text("Jl. Raya Telaga Sarangan, RT.07/RW.01", 105, 25, null, null, "center");
    doc.text("Telp : 0812-3456-7891", 105, 35, null, null, "center");
    doc.text("Magetan Jawa Tengah", 105, 45, null, null, "center");
    
    // Line separator
    doc.line(10, 48, 200, 48);
    
    // Customer Information
    doc.setFont("helvetica", "normal");
    doc.text("Nama:", 10, 55);
    doc.text(name, 50, 55);
    
    doc.text("No. Telp:", 10, 65);
    doc.text(phone, 50, 65);
    
    doc.text("Kode Booking:", 10, 75);
    doc.text(kode_booking, 50, 75);
    
    doc.text("Status:", 150, 65);
    doc.text(status, 150, 75);
    
    // Line separator
    doc.line(10, 80, 200, 80);
    
    // Booking Information
    doc.setFont("helvetica", "bold");
    doc.text("Tipe Kamar", 10, 90);
    doc.text("Tgl. Masuk", 45, 90);
    doc.text("Tgl. Keluar", 80, 90);
    doc.text("Jumlah Hari/Malam", 115, 90);
    doc.text("Jumlah Rupiah", 165, 90);
    
    doc.setFont("helvetica", "normal");
    doc.text(roomType, 10, 100);
    doc.text(checkIn, 45, 100);
    doc.text(checkOut, 80, 100);
    doc.text(nights + " Hari", 115, 100);
    doc.text(formatCurrency(amount), 165, 100);
    
    // Line separator
    doc.line(10, 110, 200, 110);
    
    // Total Payment
    doc.setFont("helvetica", "bold");
    doc.text("TOTAL PEMBAYARAN :", 10, 120);
    doc.text(formatCurrency(amount), 60, 120);
    
    doc.save('Invoice_Reservasi_' + name + '.pdf');
}

function formatCurrency(amount) {
    return 'Rp ' + amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}
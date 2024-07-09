// Function to handle 'others' checkbox change
document.getElementById('others').addEventListener('change', function() {
    var othersDetails = document.getElementById('othersDetails');
    var othersText = document.getElementById('othersText');
    if (this.checked) {
        othersDetails.classList.remove('hidden');
        othersText.setAttribute('required', 'required');
    } else {
        othersDetails.classList.add('hidden');
        othersText.removeAttribute('required');
    }
});

// Function to handle 'book for others' radio button change
document.getElementById('bookForOthers').addEventListener('change', function() {
    var guestNameField = document.getElementById('guestNameField');
    guestNameField.classList.remove('hidden');
    document.getElementById('guestName').setAttribute('required', 'required');
});

// Function to handle 'same as booker' radio button change
document.getElementById('sameAsBooker').addEventListener('change', function() {
    var guestNameField = document.getElementById('guestNameField');
    guestNameField.classList.add('hidden');
    document.getElementById('guestName').removeAttribute('required');
});

// Function to handle 'lama inap' change
document.getElementById('lamaInap').addEventListener('change', function() {
    var lamaInap = parseInt(this.value);
    var hargaPerMalam = harga_diskon; // harga_diskon should be defined in the global scope
    var hargaKamar = hargaPerMalam * lamaInap;
    var hargaTotal = hargaKamar;

    document.getElementById('hargaKamar').innerText = 'Rp ' + hargaKamar.toLocaleString('id-ID');
    document.getElementById('hargaTotal').innerText = 'Rp ' + hargaTotal.toLocaleString('id-ID');

    var checkInDate = new Date(check_in_date); // check_in_date should be defined in the global scope
    checkInDate.setDate(checkInDate.getDate() + lamaInap);
    var options = { day: '2-digit', month: '2-digit', year: 'numeric' };
    var checkOutDateStr = checkInDate.toLocaleDateString('id-ID', options);
    document.getElementById('checkOutDate').innerText = 'Check-out: ' + checkOutDateStr;
});

// Function to handle page load
document.addEventListener('DOMContentLoaded', function() {
    var hargaNormal = harga_normal; // harga_normal should be defined in the global scope
    var hargaDiskon = harga_diskon; // harga_diskon should be defined in the global scope
    var checkInDate = new Date(check_in_date); // check_in_date should be defined in the global scope
    var options = { day: '2-digit', month: '2-digit', year: 'numeric' };
    var checkInDateStr = checkInDate.toLocaleDateString('id-ID', options);

    document.querySelector('.discounted-price').innerText = 'Rp ' + hargaNormal.toLocaleString('id-ID');
    document.querySelector('.total-price').innerText = 'Rp ' + hargaDiskon.toLocaleString('id-ID');
    document.querySelector('#hargaKamar').innerText = 'Rp ' + hargaDiskon.toLocaleString('id-ID');
    document.querySelector('#hargaTotal').innerText = 'Rp ' + hargaDiskon.toLocaleString('id-ID');
    document.querySelector('.hotel-info-card p').innerText = 'Check-in: ' + checkInDateStr;
});

document.getElementById('submitBooking').addEventListener('click', function() {
    var bookingCode = 'Deluxe' + new Date().getTime();
    var createdAt = new Date().toISOString();
    var updatedAt = new Date().toISOString();
    var pesananUntuk = $('input[name="pesananUntuk"]:checked').val();
    var guestName = (pesananUntuk === 'Orang Lain') ? $('#guestName').val() : $('#namaLengkap').val();

    if (pesananUntuk === 'Orang Lain' && !guestName) {
        Swal.fire({
            title: 'Error!',
            text: 'Nama Lengkap Tamu harus diisi jika memesan untuk orang lain.',
            icon: 'error',
            confirmButtonText: 'OK'
        });
        return;
    }

    var lamaInap = parseInt(document.getElementById('lamaInap').value);
    var hargaPerMalam = harga_diskon;
    var hargaKamar = hargaPerMalam * lamaInap;

    var diskon = parseInt(document.getElementById('hargaDiskon').innerText.replace('- Rp ', '').replace('.', '')) || 0;
    var hargaTotal = hargaKamar - diskon;

    var bookingData = {
        bookingCode: bookingCode,
        namaLengkap: $('#namaLengkap').val(),
        email: $('#email').val(),
        nomorHandphone: $('#countryCode').val() + $('#nomorHandphone').val(),
        pesananUntuk: pesananUntuk,
        guestName: guestName,
        lamaInap: lamaInap,
        permintaanKhusus: [],
        hargaTotal: hargaTotal,
        diskon: diskon,
        kodeVoucher: document.getElementById('kodeVoucher').value 

    };

    $('.form-check-input:checked').each(function() {
        if ($(this).val() !== 'others') {
            bookingData.permintaanKhusus.push($(this).val());
        }
    });

    if ($('#others').is(':checked')) {
        bookingData.permintaanKhusus.push($('#othersText').val());
    }

    bookingData.hargaNormal = harga_normal;
    bookingData.hargaDiskon = harga_diskon;
    bookingData.hargaTotal = hargaTotal;
    bookingData.checkInDate = check_in_date_display;
    bookingData.checkOutDate = $('#checkOutDate').text().split(': ')[1];
    bookingData.createdAt = createdAt;
    bookingData.updatedAt = updatedAt;

    $.ajax({
        url: '/deluxe_save_booking',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(bookingData),
        success: function(response) {
            payNow(bookingCode, hargaTotal);
        },
        error: function(error) {
            Swal.fire({
                title: 'Error!',
                text: 'Terjadi kesalahan saat menyimpan data booking.',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        }
    });
});

document.getElementById('submitKodeVoucher').addEventListener('click', function() {
    var kodeVoucher = document.getElementById('kodeVoucher').value;
    var voucherDescription = document.getElementById('voucherDescription');
    var lamaInap = parseInt(document.getElementById('lamaInap').value);
    var hargaPerMalam = harga_diskon; // Adjust as necessary to reflect correct price per night

    var hargaKamar = hargaPerMalam * lamaInap;
    var tipeKamar = 'Deluxe';

    // Reset harga total dan diskon sebelum validasi voucher baru
    var resetHargaKamar = hargaPerMalam * lamaInap;
    document.getElementById('hargaTotal').innerText = 'Rp ' + resetHargaKamar.toLocaleString('id-ID');
    document.getElementById('diskonRow').classList.add('d-none');
    document.getElementById('hargaDiskon').innerText = '- Rp 0';

    fetch('/validate_voucher', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ kode_voucher: kodeVoucher, lama_inap: lamaInap, harga_kamar: hargaKamar, tipe_kamar: tipeKamar })
    })
    .then(response => response.json())
    .then(data => {
        if (data.valid) {
            var diskon = data.diskon;
            var hargaTotal = hargaKamar - diskon;
            document.getElementById('hargaTotal').innerText = 'Rp ' + hargaTotal.toLocaleString('id-ID');
            document.getElementById('diskonRow').classList.remove('d-none');
            document.getElementById('hargaDiskon').innerText = '- Rp ' + diskon.toLocaleString('id-ID');
            voucherDescription.textContent = data.message;
            voucherDescription.classList.remove('text-danger');
            voucherDescription.classList.add('text-success', 'voucher-message-success');
            voucherDescription.innerHTML = data.message + '<br><span>' + data.description + '</span>';
            
            // Tampilkan tombol reset setelah voucer berhasil
            document.getElementById('resetKodeVoucher').classList.remove('d-none');
        } else {
            voucherDescription.textContent = data.message;
            voucherDescription.classList.remove('text-success');
            voucherDescription.classList.add('text-danger', 'voucher-message-error');

            // Sembunyikan tombol reset jika voucer tidak valid
            document.getElementById('resetKodeVoucher').classList.add('d-none');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        voucherDescription.textContent = 'Terjadi kesalahan. Silakan coba lagi.';
        voucherDescription.classList.remove('text-success');
        voucherDescription.classList.add('text-danger', 'voucher-message-error');

        // Sembunyikan tombol reset jika terjadi kesalahan
        document.getElementById('resetKodeVoucher').classList.add('d-none');
    });
});

document.getElementById('resetKodeVoucher').addEventListener('click', function() {
    var voucherDescription = document.getElementById('voucherDescription');
    var lamaInap = parseInt(document.getElementById('lamaInap').value);
    var hargaPerMalam = harga_diskon; // Adjust as necessary to reflect correct price per night

    var hargaKamar = hargaPerMalam * lamaInap;

    document.getElementById('kodeVoucher').value = '';
    document.getElementById('hargaTotal').innerText = 'Rp ' + hargaKamar.toLocaleString('id-ID');
    document.getElementById('diskonRow').classList.add('d-none');
    document.getElementById('hargaDiskon').innerText = '- Rp 0';
    voucherDescription.textContent = '';
    voucherDescription.classList.remove('text-success', 'text-danger', 'voucher-message-success', 'voucher-message-error');
    
    // Sembunyikan tombol reset setelah voucer direset
    document.getElementById('resetKodeVoucher').classList.add('d-none');
});

// Function to handle 'lama inap' change to reapply voucher
document.getElementById('lamaInap').addEventListener('change', function() {
    document.getElementById('submitKodeVoucher').click();
});

// Function to handle payment
function payNow(bookingCode, hargaTotal) {
    $.getJSON(`/payment_token/${bookingCode}`, function(data) {
        snap.pay(data.token, {
            onSuccess: function(result) {
                $.ajax({
                    url: '/update_booking_status',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ booking_code: bookingCode, new_status: 'Pembayaran Berhasil', harga_total: hargaTotal }),
                    success: function(data) {
                        if (data.result === 'success') {
                            var kodeVoucher = document.getElementById('kodeVoucher').value;
                            $.ajax({
                                url: '/mengurangi_kuota',
                                type: 'POST',
                                contentType: 'application/json',
                                data: JSON.stringify({ kodeVoucher: kodeVoucher }),
                                success: function(data) {
                                    if (data.success) {
                                        window.location.href = '/user/room/booking/deluxe-room/payment-success';
                                    } else {
                                        alert('Gagal mengurangi kuota voucher: ' + data.message);
                                    }
                                },
                                error: function(error) {
                                    alert('Terjadi kesalahan saat mengurangi kuota voucher.');
                                    console.error('Error:', error);
                                }
                            });
                        } else {
                            alert('Gagal memperbarui status booking: ' + data.message);
                        }
                    }
                });
            },
            onPending: function(result) {
                $.post("/booking_dibatalkan", { booking_id: bookingCode }, function(data) {
                    if (data.result === 'success') {
                        Swal.fire({
                            icon: 'warning',
                            title: 'Pembayaran gagal',
                            text: 'Pembayaran gagal dan booking dibatalkan.',
                            showConfirmButton: false,
                            timer: 1500
                        }).then(() => {
                            window.location.href = '/user/reservasi';
                        });
                    } else {
                        Swal.fire({
                            icon: 'error',
                            title: 'Gagal',
                            text: 'Gagal membatalkan booking: ' + data.msg,
                            showConfirmButton: true
                        });
                    }
                });                             
            },
            onError: function(result) {
                $.post("/booking_dibatalkan", { booking_id: bookingCode }, function(data) {
                    if (data.result === 'success') {
                        Swal.fire({
                            icon: 'warning',
                            title: 'Pembayaran gagal',
                            text: 'Pembayaran gagal dan booking dibatalkan.',
                            showConfirmButton: false,
                            timer: 1500
                        }).then(() => {
                            window.location.href = '/user/book';
                        });
                    } else {
                        Swal.fire({
                            icon: 'error',
                            title: 'Gagal',
                            text: 'Gagal membatalkan booking: ' + data.msg,
                            showConfirmButton: true
                        });
                    }
                });
            },
            onClose: function() {
                Swal.fire({
                    icon: 'warning',
                    title: 'Pembayaran Ditutup',
                    text: 'Anda menutup popup tanpa menyelesaikan pembayaran.',
                    showConfirmButton: true
                });                    
            }
        });
    });
}

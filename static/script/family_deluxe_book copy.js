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

// Function to handle booking submission
document.getElementById('submitBooking').addEventListener('click', function() {
    var bookingCode = 'FamilyDlx' + new Date().getTime();
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

    var bookingData = {
        bookingCode: bookingCode,
        namaLengkap: $('#namaLengkap').val(),
        email: $('#email').val(),
        nomorHandphone: $('#countryCode').val() + $('#nomorHandphone').val(),
        pesananUntuk: pesananUntuk,
        guestName: guestName,
        lamaInap: $('#lamaInap').val(),
        permintaanKhusus: []
    };

    $('.form-check-input:checked').each(function() {
        if ($(this).val() !== 'others') {
            bookingData.permintaanKhusus.push($(this).val());
        }
    });

    if ($('#others').is(':checked')) {
        bookingData.permintaanKhusus.push($('#othersText').val());
    }

    bookingData.hargaNormal = harga_normal; // harga_normal should be defined in the global scope
    bookingData.hargaDiskon = harga_diskon; // harga_diskon should be defined in the global scope
    bookingData.hargaTotal = harga_diskon * bookingData.lamaInap;
    bookingData.checkInDate = check_in_date_display; // check_in_date_display should be defined in the global scope
    bookingData.checkOutDate = $('#checkOutDate').text().split(': ')[1];
    bookingData.createdAt = createdAt;
    bookingData.updatedAt = updatedAt;

    $.ajax({
        url: '/family_deluxe_save_booking',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(bookingData),
        success: function(response) {
            payNow(bookingCode);
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

// Function to handle payment
function payNow(bookingCode) {
    $.getJSON(`/payment_token/${bookingCode}`, function(data) {
        snap.pay(data.token, {
            onSuccess: function(result) {
                $.ajax({
                    url: '/update_booking_status',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ booking_code: bookingCode, new_status: 'Pembayaran Berhasil' }),
                    success: function(data) {
                        if (data.result === 'success') {
                            window.location.href = '/user/room/booking/family-deluxe-room/payment-success';
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

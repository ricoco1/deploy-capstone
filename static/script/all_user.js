//script halaman Profile user
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.delete-icon').forEach(icon => {
        icon.addEventListener('click', () => {
            const reviewId = icon.getAttribute('data-review-id');
            Swal.fire({
                title: 'Apakah Anda yakin?',
                text: "Anda tidak dapat mengembalikan ini!",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#3085d6',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Ya, hapus!'
            }).then((result) => {
                if (result.isConfirmed) {
                    fetch(`/delete_review/${reviewId}`, {
                        method: 'DELETE'
                    })
                    .then(response => {
                        if (response.ok) {
                            Swal.fire(
                                'Dihapus!',
                                'Review Anda telah dihapus.',
                                'success'
                            ).then(() => {
                                location.reload();
                            });
                        } else {
                            Swal.fire(
                                'Gagal!',
                                'Gagal menghapus review Anda.',
                                'error'
                            );
                        }
                    });
                }
            });
        });
    });
});

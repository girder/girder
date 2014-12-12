
describe('Test upload widget non-standard options', function () {
    it('create the widget', function () {
        runs(function () {
            var uploadWidget = new girder.views.UploadWidget({
                noParent: true,
                modal: false,
                title: null,
                el: 'body'
            }).render();

            expect($('.modal').length).toBe(0);
            expect($('#g-upload-form h4').length).toBe(0);
            expect($('.g-dialog-subtitle').length).toBe(0);
            expect($('.g-drop-zone:visible').length).toBe(1);
            expect($('.g-start-upload.btn.disabled:visible').length).toBe(1);
            expect($('.g-overall-progress-message').text()).toBe('No files selected');
        });
    });
});

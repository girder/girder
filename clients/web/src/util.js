(function () {
    // A private function to upload files, abstracted over the container model.
    var uploadToEntity = function (cfg, EntityModel) {
        var blob,
            folder,
            file;

        cfg = cfg || {};

        // At a minimum, we need a place to upload to, a name for the new file,
        // and data to upload.
        if (!cfg.id) {
            throw new Error("'id' required");
        }

        if (!cfg.name) {
            throw new Error("'name' required");
        }

        if (!cfg.data) {
            throw new Error("'data' required");
        }

        // Emulate the File interface by creating a blob and stuffing in the
        // name and type properties.
        blob = new Blob([cfg.data]);
        blob.name = cfg.name;
        blob.type = cfg.type;

        // Create a Girder container model.
        folder = new EntityModel({
            _id: cfg.folderId
        });

        // Create a Girder file model.
        file = new girder.models.FileModel();

        // Attach the callbacks (defaulting to noop if the user did not supply
        // them).
        file.on("g:upload.complete", cfg.complete || Backbone.$.noop);
        file.on("g:upload.chunkSent", cfg.chunkSent || Backbone.$.noop);
        file.on("g:upload.error", cfg.error || Backbone.$.noop);
        file.on("g:upload.errorStarting", cfg.errorStarting || Backbone.$.noop);
        file.on("g:upload.progress", cfg.progress || Backbone.$.noop);

        // Execute the upload.
        file.upload(folder, blob);
    };

    girder.util = {
        uploadToFolder: _.partial(uploadToEntity, _, girder.models.FolderModel),
        uploadToItem: _.partial(uploadToEntity, _, girder.models.ItemModel)
    };
}());

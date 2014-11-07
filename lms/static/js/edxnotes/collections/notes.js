;(function (define, undefined) {
    'use strict';
    define([
        'backbone', 'js/edxnotes/models/note'
    ], function (Backbone, NoteModel) {
        var NotesCollection = Backbone.Collection.extend({
            comparator: 'updated',
            model: NoteModel
        });

        return NotesCollection;
    });
}).call(this, define || RequireJS.define);

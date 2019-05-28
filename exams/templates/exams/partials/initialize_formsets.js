var add_icon = '<i class="fa fa-plus" aria-hidden="true"></i>',
    delete_icon = '<i class="fa fa-trash" aria-hidden="true"></i>';

// add formset controls
$("#choice_formset .form-container").formset({
    prefix: '{{ revision_choice_formset.prefix }}',
    formCssClass: 'dynamic-formset1',
    addText: add_icon,
    deleteText: delete_icon,
    addCssClass: 'add-row btn btn-xs btn-primary',
    deleteCssClass: 'delete-row btn btn-xs btn-danger',
});
$("#revision_figure_formset .form-container").formset({
    prefix: '{{ revision_figure_formset.prefix }}',
    formCssClass: 'dynamic-formset2',
    addText: add_icon,
    deleteText: delete_icon,
    addCssClass: 'add-row btn btn-xs btn-primary',
    deleteCssClass: 'delete-row btn btn-xs btn-danger',
});
$("#explanation_figure_formset .form-container").formset({
    prefix: '{{ explanation_figure_formset.prefix }}',
    addText: add_icon,
    deleteText: delete_icon,
    addCssClass: 'add-row btn btn-xs btn-primary',
    deleteCssClass: 'delete-row btn btn-xs btn-danger',
});
$('.form-check-label:contains("Delete")').closest('.form-group').hide();

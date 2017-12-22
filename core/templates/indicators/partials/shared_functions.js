// START OF SHARED FUNCTIONS
function unpack(key, is_int) {
  if (is_int){
    return rows.map(function(row) { return parseInt(row[key]); });
  } else {
    return rows.map(function(row) { return row[key]; });
  }
}

function get_change_percentage(count_field, row){
  yesterday = moment(row['date']).subtract(1, 'days')
  yesterday_str = yesterday.format('YYYY-MM-DD')

  previous_row = rows.find(function(item){ return item['date'] == yesterday_str });
  if (row[count_field] == 0 || previous_row === undefined){
    percentage = 0
  } else {
    diff = row[count_field] - previous_row[count_field];
    percentage = (diff / row[count_field]) * 100
    percentage = percentage.toPrecision(2)
  }
  if (percentage > 0){
    percentage = '+' + percentage
  }
  return percentage
}

function get_hover(count_field, batch_pk){
  if (batch_pk){
    count_field = count_field + '_' + batch_pk;
  }

  return rows.map(function(row) {
    end_date = moment(row['date'])
    start_date = moment(row['date']).subtract(30, 'days')

    // Calculate change
    percentage = get_change_percentage(count_field, row)

    end_date_str = end_date.format('DD MMM')
    start_date_str = start_date.format('DD MMM')
    return '<span style=\'font-weight: 700; text-decoration: underline;\'>' + start_date_str + '‒' + end_date_str + '</span><br>' +  row[count_field] + ' (' + percentage + '%)'
  });
}

function get_contribution_data(batch_pk){
  revision_field = 'revision_count'
  explanation_field = 'explanation_count'
  correction_field = 'correction_count'
  mnemonic_field = 'mnemonic_count'

  if (batch_pk){
    revision_field += '_' + batch_pk
    explanation_field += '_' + batch_pk
    correction_field += '_' + batch_pk
    mnemonic_field += '_' + batch_pk
  }

  return rows.map(function(row){
    contribution_count = parseInt(row[revision_field]) + parseInt(row[explanation_field]) + parseInt(row[correction_field]) + parseInt(row[mnemonic_field])
    return contribution_count
  })
}


function get_contribution_hover(batch_pk){
  revision_field = 'revision_count'
  explanation_field = 'explanation_count'
  correction_field = 'correction_count'
  mnemonic_field = 'mnemonic_count'

  if (batch_pk){
    revision_field += '_' + batch_pk
    explanation_field += '_' + batch_pk
    correction_field += '_' + batch_pk
    mnemonic_field += '_' + batch_pk
  }

  return rows.map(function(row) {
    end_date = moment(row['date'])
    start_date = moment(row['date']).subtract(30, 'days')

    // Calculate change
    explanation_percentage = get_change_percentage(explanation_field, row)
    revision_percentage = get_change_percentage(revision_field, row)
    correction_percentage = get_change_percentage(correction_field, row)
    mnemonic_percentage = get_change_percentage(mnemonic_field, row)

    end_date_str = end_date.format('DD MMM')
    start_date_str = start_date.format('DD MMM')
    return '<span style=\'font-weight: 700; text-decoration: underline;\'>' + start_date_str + '‒' + end_date_str + '</span><br>' + 'Revisions added: ' + row[revision_field] + ' (' + revision_percentage + '%)<br>' + 'Explanation revisions added: ' + row[explanation_field] + ' (' + explanation_percentage + '%)<br>' + 'Corrections added: ' + row[correction_field] + ' (' + correction_percentage + '%)<br>' + 'Mnemonics added: ' + row[mnemonic_field] + ' (' + mnemonic_percentage + '%)'
  });
}

{% if exam_date_json %}
exam_date_input = JSON.parse('{{ exam_date_json|safe }}')
exam_dates = Object.keys(exam_date_input)
exam_dates_hovertexts = Object.values(exam_date_input)
exam_dates_counts = exam_dates.map(function(date){ row = rows.find(function(row){ return row['date'] == date}); return row['user_count']})
var exam_date_data = {
  x: exam_dates,
  y: exam_dates_counts,
  text: exam_dates_hovertexts,
  mode: 'markers',
  type: 'scatter',
  hoverinfo: 'text',
  showlegend: false,
  marker: { size: 12 },
}
{% else %}
var exam_date_data = {}
{% endif %}
// END OF SHARED FUNCTIONS

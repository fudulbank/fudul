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
  return percentage
}

function get_hover(count_field, batch_pk){
  count_field = count_field + '_' + batch_pk;
  return rows.map(function(row) {
    end_date = moment(row['date'])
    start_date = moment(row['date']).subtract(30, 'days')

    // Calculate change
    percentage = get_change_percentage(count_field, row)

    end_date_str = end_date.format('DD MMM')
    start_date_str = start_date.format('DD MMM')
    return row[count_field] + ' (' + percentage + '%)<br>' + start_date_str + '‒' + end_date_str
  });
}

function get_contribution_data(batch_pk){
  revision_field = 'revision_count'
  explanation_field = 'explanation_count'

  if (batch_pk){
    revision_field += '_' + batch_pk
    explanation_field += '_' + batch_pk
  }

  return rows.map(function(row){
    contribution_count = parseInt(row[revision_field]) + parseInt(row[explanation_field])
    return contribution_count
  })
}


function get_contribution_hover(batch_pk){
  revision_field = 'revision_count'
  explanation_field = 'explanation_count'

  if (batch_pk){
    revision_field += '_' + batch_pk
    explanation_field += '_' + batch_pk
  }

  return rows.map(function(row) {
    end_date = moment(row['date'])
    start_date = moment(row['date']).subtract(30, 'days')

    // Calculate change
    explanation_percentage = get_change_percentage(explanation_field, row)
    revision_percentage = get_change_percentage(revision_field, row)

    end_date_str = end_date.format('DD MMM')
    start_date_str = start_date.format('DD MMM')
    return 'Revisions added: ' + row[revision_field] + ' (' + revision_percentage + '%)<br>' + 'Explanations added: ' + row[explanation_field] + ' (' + explanation_percentage + '%)<br>' + start_date_str + '‒' + end_date_str
  });
}

// END OF SHARED FUNCTIONS

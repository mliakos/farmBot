var done = arguments[0]; 
var time;
if($('#commands_outgoings > table:nth-child(1) > tbody:nth-child(1)').find('tr.command-row').length != 0){
    time = jQuery("img[src*='return']").closest('tr').children().eq(2)[0].innerText;
}else{
    time = undefined
}
 

done(time)
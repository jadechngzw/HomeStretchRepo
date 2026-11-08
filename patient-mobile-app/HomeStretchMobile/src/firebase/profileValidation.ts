export function profileFields(name: string, dob: string, now = new Date()) {
  const full_name = name.trim().replace(/\s+/g, ' ');
  if (full_name.length < 2 || full_name.length > 100) throw new Error('Enter your full name.');
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(dob.trim());
  if (!match) throw new Error('Enter your date of birth as MM/DD/YYYY.');
  const [, mm, dd, yyyy] = match;
  const date = new Date(+yyyy, +mm - 1, +dd);
  if (+yyyy < 1900 || date.getFullYear() !== +yyyy || date.getMonth() !== +mm - 1 || date.getDate() !== +dd || date > now)
    throw new Error('Enter a valid date of birth that is not in the future.');
  return {full_name, date_of_birth: `${yyyy}-${mm}-${dd}`};
}
export function formatBirthInput(value:string) {
  const digits=value.replace(/\D/g,'').slice(0,8);
  return digits.length<=2?digits:digits.length<=4?`${digits.slice(0,2)}/${digits.slice(2)}`:`${digits.slice(0,2)}/${digits.slice(2,4)}/${digits.slice(4)}`;
}

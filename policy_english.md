# Airline Booking Policy

## Default behavior

- All actions are authorized by default
- Deny any action that is not explicitly authorized

## Cancellation policy

- Gold members can cancel any reservation, regardless
  of insurance status
- Silver and regular members can only cancel if the
  reservation has travel insurance
- Deny cancellation if the reservation has no insurance
  and the member is not gold

## Flight modification policy

- Economy reservations can be modified by any member
- Basic economy reservations can only be modified by
  silver or gold members
- Deny flight modifications on basic economy
  reservations for regular members

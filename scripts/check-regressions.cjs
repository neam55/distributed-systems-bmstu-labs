// Integration regressions against the running Docker Compose services.
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

const baseUrl = process.env.BASE_URL || 'http://localhost:8080';
const loyaltyUrl = process.env.LOYALTY_URL || 'http://localhost:8050';
const username = `lab02-regression-${randomUUID()}`;
const headers = { 'X-User-Name': username, 'Content-Type': 'application/json' };

async function request(url, method = 'GET', body, status = 200) {
  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });
  const text = await response.text();
  assert.equal(response.status, status, `${method} ${url}: ${text}`);
  return text ? JSON.parse(text) : null;
}

async function main() {
  const first = await request(`${baseUrl}/api/v1/hotels?page=1&size=1`);
  const zero = await request(`${baseUrl}/api/v1/hotels?page=0&size=1`);
  assert.equal(zero.page, 0);
  assert.deepEqual(zero.items, first.items);
  await request(`${baseUrl}/api/v1/hotels?page=-1&size=1`, 'GET', undefined, 400);
  console.log('PASS: page=0 returns the first page; negative pages are rejected');

  // A positive baseline makes duplicate decrements visible despite the zero floor.
  await request(`${baseUrl}/api/v1/loyalty`);
  await request(loyaltyUrl + '/api/v1/loyalty', 'PATCH', { delta: 25 });
  const booking = {
    hotelUid: first.items[0].hotelUid,
    startDate: '2021-10-08',
    endDate: '2021-10-11',
  };
  const created = await request(`${baseUrl}/api/v1/reservations`, 'POST', booking);
  const url = `${baseUrl}/api/v1/reservations/${created.reservationUid}`;
  await Promise.all(Array.from({ length: 12 }, () => request(url, 'DELETE', undefined, 204)));
  await request(url, 'DELETE', undefined, 204);
  assert.equal((await request(`${baseUrl}/api/v1/loyalty`)).reservationCount, 25);
  const canceled = await request(url);
  assert.equal(canceled.status, 'CANCELED');
  assert.equal(canceled.payment.status, 'CANCELED');
  console.log('PASS: 12 concurrent and one repeated cancellation decrement loyalty once');

  const bookings = await Promise.all(
    Array.from({ length: 8 }, () => request(`${baseUrl}/api/v1/reservations`, 'POST', booking)),
  );
  assert.equal((await request(`${baseUrl}/api/v1/loyalty`)).reservationCount, 33);
  await Promise.all(bookings.map(item => request(
    `${baseUrl}/api/v1/reservations/${item.reservationUid}`, 'DELETE', undefined, 204,
  )));
  assert.equal((await request(`${baseUrl}/api/v1/loyalty`)).reservationCount, 25);
  console.log('PASS: concurrent bookings and distinct cancellations do not lose counter updates');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

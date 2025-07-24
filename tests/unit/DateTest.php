<?php

declare(strict_types=1);

namespace Infoclimat\Date\Test;

require_once __ROOT__ . '/date.php';

use Infoclimat\Date\Duration;
use PHPUnit\Framework\TestCase;

use function Infoclimat\Date\better_gmmktime;
use function Infoclimat\Date\day;
use function Infoclimat\Date\DD;
use function Infoclimat\Date\DD_of;
use function Infoclimat\Date\format_two_digits;
use function Infoclimat\Date\hh;
use function Infoclimat\Date\hh_of;
use function Infoclimat\Date\hours_of;
use function Infoclimat\Date\ii;
use function Infoclimat\Date\ii_of;
use function Infoclimat\Date\minutes;
use function Infoclimat\Date\minutes_of;
use function Infoclimat\Date\MM;
use function Infoclimat\Date\MM_of;
use function Infoclimat\Date\month;
use function Infoclimat\Date\year;
use function Infoclimat\Date\YYYY_of;

final class DateTest extends TestCase
{

    protected function setUp(): void
    {
        date_default_timezone_set('UTC');
    }

    public function testBetterGmmktime(): void
    {
        $this->assertEquals(
            strtotime('2000-06-15T00:00:00Z'),
            better_gmmktime(2000, 6, 15)
        );
        $this->assertEquals(
            strtotime('2000-06-15T12:00:00Z'),
            better_gmmktime(2000, 6, 15, 12)
        );
        $this->assertEquals(
            strtotime('2000-06-15T12:30:00Z'),
            better_gmmktime(2000, 6, 15, 12, 30)
        );
        $this->assertEquals(
            strtotime('2000-06-15T12:30:45Z'),
            better_gmmktime(2000, 6, 15, 12, 30, 45)
        );
    }

    public function testFormatTwoDigits(): void
    {
        $this->assertEquals("06", format_two_digits(6));
        $this->assertEquals("06", format_two_digits("6"));
        $this->assertEquals("06", format_two_digits("06"));
        $this->assertEquals("12", format_two_digits(12));
        $this->assertEquals("12", format_two_digits("12"));
    }

    public function testTwoDigitsHelpers(): void
    {
        $year = 2000;
        $month = 6;
        $day = 1;
        $hour = 9;
        $minute = 5;
        $this->assertEquals('06', MM($month));
        $this->assertEquals('01', DD($day));
        $this->assertEquals('09', hh($hour));
        $this->assertEquals('05', ii($minute));
    }

    public function testTimestampHelpers(): void
    {
        $t = strtotime('2000-06-15T12:30:45Z');
        $this->assertEquals(2000, year($t));
        $this->assertEquals(6, month($t));
        $this->assertEquals(15, day($t));
        $this->assertEquals(12, hours_of($t));
        $this->assertEquals(30, minutes_of($t));
        $t = strtotime('2000-06-01T09:05:45Z');
        $this->assertEquals('2000', YYYY_of($t));
        $this->assertEquals('06', MM_of($t));
        $this->assertEquals('01', DD_of($t));
        $this->assertEquals('09', hh_of($t));
        $this->assertEquals('05', ii_of($t));
    }

    /**
     * A month is considered to have 31 days.
     * A year is considered to have 366 days.
     */
    public function testDurationFrom(): void
    {
        $duration = Duration::from([
            'years'        => 1,
            'months'       => 6,
            'days'         => 15,
            'hours'        => 12,
            'minutes'      => 30,
            'seconds'      => 45,
            'milliseconds' => 999,
        ]);
        $ONE_SECOND_IN_MILLISECONDS = 1000;
        $ONE_MINUTE_IN_MILLISECONDS = 60 * $ONE_SECOND_IN_MILLISECONDS;
        $ONE_HOUR_IN_MILLISECONDS = 60 * $ONE_MINUTE_IN_MILLISECONDS;
        $ONE_DAY_IN_MILLISECONDS = 24 * $ONE_HOUR_IN_MILLISECONDS;
        $ONE_MONTH_IN_MILLISECONDS = 31 * $ONE_DAY_IN_MILLISECONDS;
        $ONE_YEAR_IN_MILLISECONDS = 366 * $ONE_DAY_IN_MILLISECONDS;
        $expected = 0
            + 1 * $ONE_YEAR_IN_MILLISECONDS
            + 6 * $ONE_MONTH_IN_MILLISECONDS
            + 15 * $ONE_DAY_IN_MILLISECONDS
            + 12 * $ONE_HOUR_IN_MILLISECONDS
            + 30 * $ONE_MINUTE_IN_MILLISECONDS
            + 45 * $ONE_SECOND_IN_MILLISECONDS
            + 999;
        $this->assertEquals($expected, $duration->inMilliseconds());
    }

    public function testDurationInMicroseconds(): void
    {
        $duration = Duration::from([
            'years'        => 1,
            'months'       => 6,
            'days'         => 15,
            'hours'        => 12,
            'minutes'      => 30,
            'seconds'      => 45,
            'milliseconds' => 999,
        ]);
        $ONE_MILLISECOND_IN_MICROSECONDS = 1000;
        $ONE_SECOND_IN_MICROSECONDS = 1000 * $ONE_MILLISECOND_IN_MICROSECONDS;
        $ONE_MINUTE_IN_MICROSECONDS = 60 * $ONE_SECOND_IN_MICROSECONDS;
        $ONE_HOUR_IN_MICROSECONDS = 60 * $ONE_MINUTE_IN_MICROSECONDS;
        $ONE_DAY_IN_MICROSECONDS = 24 * $ONE_HOUR_IN_MICROSECONDS;
        $ONE_MONTH_IN_MICROSECONDS = 31 * $ONE_DAY_IN_MICROSECONDS;
        $ONE_YEAR_IN_MICROSECONDS = 366 * $ONE_DAY_IN_MICROSECONDS;
        $expected = 0
            + 1 * $ONE_YEAR_IN_MICROSECONDS
            + 6 * $ONE_MONTH_IN_MICROSECONDS
            + 15 * $ONE_DAY_IN_MICROSECONDS
            + 12 * $ONE_HOUR_IN_MICROSECONDS
            + 30 * $ONE_MINUTE_IN_MICROSECONDS
            + 45 * $ONE_SECOND_IN_MICROSECONDS
            + 999 * $ONE_MILLISECOND_IN_MICROSECONDS;
        $this->assertEquals($expected, $duration->inMicroseconds());
    }

    public function testDurationInMilliseconds(): void
    {
        $duration = Duration::from([
            'years'        => 1,
            'months'       => 6,
            'days'         => 15,
            'hours'        => 12,
            'minutes'      => 30,
            'seconds'      => 45,
            'milliseconds' => 999,
        ]);
        $ONE_SECOND_IN_MILLISECONDS = 1000;
        $ONE_MINUTE_IN_MILLISECONDS = 60 * $ONE_SECOND_IN_MILLISECONDS;
        $ONE_HOUR_IN_MILLISECONDS = 60 * $ONE_MINUTE_IN_MILLISECONDS;
        $ONE_DAY_IN_MILLISECONDS = 24 * $ONE_HOUR_IN_MILLISECONDS;
        $ONE_MONTH_IN_MILLISECONDS = 31 * $ONE_DAY_IN_MILLISECONDS;
        $ONE_YEAR_IN_MILLISECONDS = 366 * $ONE_DAY_IN_MILLISECONDS;
        $expected = 0
            + 1 * $ONE_YEAR_IN_MILLISECONDS
            + 6 * $ONE_MONTH_IN_MILLISECONDS
            + 15 * $ONE_DAY_IN_MILLISECONDS
            + 12 * $ONE_HOUR_IN_MILLISECONDS
            + 30 * $ONE_MINUTE_IN_MILLISECONDS
            + 45 * $ONE_SECOND_IN_MILLISECONDS
            + 999;
        $this->assertEquals($expected, $duration->inMilliseconds());
    }

    public function testDurationInSeconds(): void
    {
        $duration = Duration::from([
            'years'   => 1,
            'months'  => 6,
            'days'    => 15,
            'hours'   => 12,
            'minutes' => 30,
            'seconds' => 45,
        ]);
        $ONE_MINUTE_IN_SECONDS = 60;
        $ONE_HOUR_IN_SECONDS = 60 * $ONE_MINUTE_IN_SECONDS;
        $ONE_DAY_IN_SECONDS = 24 * $ONE_HOUR_IN_SECONDS;
        $ONE_MONTH_IN_SECONDS = 31 * $ONE_DAY_IN_SECONDS;
        $ONE_YEAR_IN_SECONDS = 366 * $ONE_DAY_IN_SECONDS;
        $expected = 0
            + 1 * $ONE_YEAR_IN_SECONDS
            + 6 * $ONE_MONTH_IN_SECONDS
            + 15 * $ONE_DAY_IN_SECONDS
            + 12 * $ONE_HOUR_IN_SECONDS
            + 30 * $ONE_MINUTE_IN_SECONDS
            + 45;
        $this->assertEquals($expected, $duration->inSeconds());
    }

    public function testDurationInMinutes(): void
    {
        $this->assertEquals(3 * 60, Duration::from(['hours' => 3])->inMinutes());
        $this->assertEquals(1, Duration::from(['seconds' => 60])->inMinutes());
        $this->assertEquals(60, Duration::from(['hours' => 1])->inMinutes());
    }

    public function testDurationInHours(): void
    {
        $duration = Duration::from(['minutes' => 90]);
        $this->assertEquals(1, $duration->inHours());
        $this->assertEquals(1.5, $duration->inHours(true));
        $this->assertEquals(1, Duration::from(['minutes' => 60])->inHours());
        $this->assertEquals(24, Duration::from(['days' => 1])->inHours());
    }

    public function testDurationInDays(): void
    {
        $this->assertEquals(1, Duration::from(['hours' => 24])->inDays());
        $this->assertEquals(7, Duration::from(['weeks' => 1])->inDays());
        $this->assertEquals(31, Duration::from(['months' => 1])->inDays());
        $this->assertEquals(366, Duration::from(['years' => 1])->inDays());
    }

    public function testDurationAdd(): void
    {
        $duration = minutes(7 * 24 * 60)->add(minutes(36 * 60))->add(minutes(90));
        $this->assertEquals(7 * 24 * 60 * 60 + 36 * 60 * 60 + 90 * 60, $duration->inSeconds());
        $this->assertEquals(7 * 24 * 60 + 36 * 60 + 90, $duration->inMinutes());
        $this->assertEquals(7 * 24 + 36 + 1, $duration->inHours());
        $this->assertEquals(7 + 1, $duration->inDays());
        $this->assertEquals(1, $duration->inWeeks());
    }

    public function testDurationBetween(): void
    {
        $time_a = strtotime('2000-06-07T06:15:10Z');
        $time_b = strtotime('2000-06-22T18:45:55Z');
        $expected = Duration::from([
            'days'    => 15,
            'hours'   => 12,
            'minutes' => 30,
            'seconds' => 45,
        ]);
        $this->assertEquals($expected, Duration::between($time_a, $time_b));
    }

    public function testDurationDistance(): void
    {
        $time_a = strtotime('2000-06-07T06:15:10Z');
        $time_b = strtotime('2000-06-22T18:45:55Z');
        $expected = Duration::from([
            'days'    => 15,
            'hours'   => 12,
            'minutes' => 30,
            'seconds' => 45,
        ]);
        $this->assertEquals($expected, Duration::distance($time_a, $time_b));
        $this->assertEquals($expected, Duration::distance($time_b, $time_a));
        $this->assertTrue(Duration::distance($time_b, $time_a)->equals(Duration::distance($time_a, $time_b)));
    }

    public function testDuration_givenEqualDurations(): void
    {
        $duration_a = Duration::from([
            'years'        => 1,
            'months'       => 6,
            'days'         => 15,
            'hours'        => 12,
            'minutes'      => 30,
            'seconds'      => 45,
            'milliseconds' => 999,
        ]);
        $duration_b = Duration::from([
            'years'        => 1,
            'months'       => 6,
            'days'         => 15,
            'hours'        => 12,
            'minutes'      => 30,
            'seconds'      => 45,
            'milliseconds' => 999,
        ]);
        $this->assertTrue($duration_a->equals($duration_b));
        $this->assertTrue($duration_a->lessThanOrEqualTo($duration_b));
        $this->assertTrue($duration_b->lessThanOrEqualTo($duration_a));
        $this->assertTrue($duration_a->greaterThanOrEqualTo($duration_b));
        $this->assertTrue($duration_b->greaterThanOrEqualTo($duration_a));
        $this->assertFalse($duration_a->lessThan($duration_b));
        $this->assertFalse($duration_b->lessThan($duration_a));
        $this->assertFalse($duration_a->greaterThan($duration_b));
        $this->assertFalse($duration_b->greaterThan($duration_a));
    }

    public function testDuration_givenDifferentDurations(): void
    {
        $duration_a = Duration::from([
            'years'        => 1,
            'months'       => 6,
            'days'         => 15,
            'hours'        => 12,
            'minutes'      => 30,
            'seconds'      => 45,
            'milliseconds' => 222,
        ]);
        $duration_b = Duration::from([
            'years'        => 2,
            'months'       => 7,
            'days'         => 16,
            'hours'        => 13,
            'minutes'      => 35,
            'seconds'      => 55,
            'milliseconds' => 888,
        ]);
        $this->assertFalse($duration_a->equals($duration_b));
        $this->assertTrue($duration_a->lessThanOrEqualTo($duration_b));
        $this->assertFalse($duration_b->lessThanOrEqualTo($duration_a));
        $this->assertFalse($duration_a->greaterThanOrEqualTo($duration_b));
        $this->assertTrue($duration_b->greaterThanOrEqualTo($duration_a));
        $this->assertTrue($duration_a->lessThan($duration_b));
        $this->assertFalse($duration_b->lessThan($duration_a));
        $this->assertFalse($duration_a->greaterThan($duration_b));
        $this->assertTrue($duration_b->greaterThan($duration_a));
    }

    public function testMinutes(): void
    {
        $duration = minutes(90);
        $this->assertEquals(90 * 60, $duration->inSeconds());
        $this->assertEquals(90, $duration->inMinutes());
        $this->assertEquals(1, $duration->inHours());
        $this->assertEquals(1.5, $duration->inHours(true));
        $this->assertEquals(60, minutes(1)->inSeconds());
        $this->assertEquals(1, minutes(1)->inMinutes());
        $this->assertEquals(1, minutes(60)->inHours());
    }
}

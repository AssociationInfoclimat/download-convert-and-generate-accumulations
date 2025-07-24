<?php

declare(strict_types=1);

namespace Infoclimat\Date;

/**
 * @return string "01"
 */
function format_two_digits(int|string $number): string
{
    return sprintf('%02d', $number);
}

function better_gmmktime(
    int $year,
    int $month,
    int $day,
    int $hour = 0,
    int $minute = 0,
    int $second = 0
): int {
    return gmmktime(
        $hour,
        $minute,
        $second,
        $month,
        $day,
        $year
    );
}

class Duration
{
    public int $milliseconds;

    public function __construct(int $milliseconds)
    {
        $this->milliseconds = $milliseconds;
    }

    public function inMicroseconds(): int
    {
        return $this->milliseconds * 1000;
    }

    public function us(): int
    {
        return $this->inMicroseconds();
    }

    public function inMilliseconds(): int
    {
        return $this->milliseconds;
    }

    public function ms(): int
    {
        return $this->inMilliseconds();
    }

    public function inSeconds(bool $exact = false): int|float
    {
        if ($exact) {
            return $this->inMilliseconds($exact) / 1000;
        }
        return (int) floor($this->inMilliseconds() / 1000);
    }

    public function s(bool $exact = false): int|float
    {
        return $this->inSeconds($exact);
    }

    public function inMinutes(bool $exact = false): int|float
    {
        if ($exact) {
            return $this->inSeconds($exact) / 60;
        }
        return (int) floor($this->inSeconds() / 60);
    }

    public function mn(bool $exact = false): int|float
    {
        return $this->inMinutes($exact);
    }

    public function inHours(bool $exact = false): int|float
    {
        if ($exact) {
            return $this->inMinutes($exact) / 60;
        }
        return (int) floor($this->inMinutes() / 60);
    }

    public function h(bool $exact = false): int|float
    {
        return $this->inHours($exact);
    }

    public function inDays(bool $exact = false): int|float
    {
        if ($exact) {
            return $this->inHours($exact) / 24;
        }
        return (int) floor($this->inHours() / 24);
    }

    public function inWeeks(bool $exact = false): int|float
    {
        if ($exact) {
            return $this->inDays($exact) / 7;
        }
        return (int) floor($this->inDays() / 7);
    }

    public function equals(Duration $other): bool
    {
        return $this->inMilliseconds() === $other->inMilliseconds();
    }

    public function lessThan(Duration $other): bool
    {
        return $this->inMilliseconds() < $other->inMilliseconds();
    }

    public function lessThanOrEqualTo(Duration $other): bool
    {
        return $this->inMilliseconds() <= $other->inMilliseconds();
    }

    public function greaterThan(Duration $other): bool
    {
        return $other->lessThan($this);
    }

    public function greaterThanOrEqualTo(Duration $other): bool
    {
        return $other->lessThanOrEqualTo($this);
    }

    public function add(Duration $other): Duration
    {
        return new Duration($this->inMilliseconds() + $other->inMilliseconds());
    }

    public function copy(): Duration
    {
        return new Duration($this->inMilliseconds());
    }

    public static function from(array $parts): Duration
    {
        $ONE_SECOND_IN_MILLISECONDS = 1000;
        $ONE_MINUTE_IN_MILLISECONDS = 60 * $ONE_SECOND_IN_MILLISECONDS;
        $ONE_HOUR_IN_MILLISECONDS = 60 * $ONE_MINUTE_IN_MILLISECONDS;
        $ONE_DAY_IN_MILLISECONDS = 24 * $ONE_HOUR_IN_MILLISECONDS;
        $ONE_WEEK_IN_MILLISECONDS = 7 * $ONE_DAY_IN_MILLISECONDS;
        $ONE_MONTH_IN_MILLISECONDS = 31 * $ONE_DAY_IN_MILLISECONDS;
        $ONE_YEAR_IN_MILLISECONDS = 366 * $ONE_DAY_IN_MILLISECONDS;
        $seconds = 0;
        $seconds += ($parts['years'] ?? 0) * $ONE_YEAR_IN_MILLISECONDS;
        $seconds += ($parts['months'] ?? 0) * $ONE_MONTH_IN_MILLISECONDS;
        $seconds += ($parts['weeks'] ?? 0) * $ONE_WEEK_IN_MILLISECONDS;
        $seconds += ($parts['days'] ?? 0) * $ONE_DAY_IN_MILLISECONDS;
        $seconds += ($parts['hours'] ?? 0) * $ONE_HOUR_IN_MILLISECONDS;
        $seconds += ($parts['minutes'] ?? 0) * $ONE_MINUTE_IN_MILLISECONDS;
        $seconds += ($parts['seconds'] ?? 0) * $ONE_SECOND_IN_MILLISECONDS;
        $seconds += ($parts['milliseconds'] ?? 0);
        return new Duration((int) $seconds);
    }

    public static function between(int $start, int $end): Duration
    {
        return new Duration(($end - $start) * 1000);
    }

    public static function distance(int $start, int $end): Duration
    {
        return new Duration(abs($end - $start) * 1000);
    }
}

function minutes(int|float $minutes): Duration
{
    return Duration::from(['minutes' => $minutes]);
}

function mn(int|float $minutes): Duration
{
    return minutes($minutes);
}

function ii(string|int $minute): string
{
    return format_two_digits($minute);
}

function hh(string|int $hour): string
{
    return format_two_digits($hour);
}

function DD(string|int $day): string
{
    return format_two_digits($day);
}

function MM(string|int $month): string
{
    return format_two_digits($month);
}

function minutes_of(int $t): int
{
    return (int) gmdate('i', $t);
}

function hours_of(int $t): int
{
    return (int) gmdate('H', $t);
}

function day(int $t): int
{
    return (int) gmdate('d', $t);
}

function month(int $t): int
{
    return (int) gmdate('m', $t);
}

function year(int $t): int
{
    return (int) gmdate('Y', $t);
}

function ii_of(int $t): string
{
    return ii(minutes_of($t));
}

function hh_of(int $t): string
{
    return hh(hours_of($t));
}

function DD_of(int $t): string
{
    return DD(day($t));
}

function MM_of(int $t): string
{
    return MM(month($t));
}

function YYYY_of(int $t): string
{
    return (string) year($t);
}

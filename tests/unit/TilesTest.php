<?php

declare(strict_types=1);

namespace Infoclimat\Tiles\Tests\Unit;

require_once __ROOT__ . '/tiles.php';
require_once __ROOT__ . '/date.php';

use PHPUnit\Framework\TestCase;

use function Infoclimat\Tiles\get_date_dictionary;
use function Infoclimat\Tiles\transform_date_dictionnary_to_timestamp;

final class TilesTest extends TestCase
{
    public function testTransformDateDictionnaryToTimestamp(): void
    {
        $date = [
            'year'   => '2000',
            'month'  => '06',
            'day'    => '15',
            'hour'   => '12',
            'minute' => '30',
        ];
        $timestamp = transform_date_dictionnary_to_timestamp($date);
        $this->assertSame(strtotime('2000-06-15T12:30:00Z'), $timestamp);
    }

    public function testGetDateDictionary(): void
    {
        $timestamp = strtotime('2000-06-15T12:30:45Z');
        $date = get_date_dictionary($timestamp);
        $this->assertSame(
            [
                'year'   => '2000',
                'month'  => '06',
                'day'    => '15',
                'hour'   => '12',
                'minute' => '30',
            ],
            $date
        );
    }

    public function testName(): void
    {
        $data = [];
        $expected = [];
        $this->assertSame($expected, $data);
        $this->assertNull(null);
        $this->assertSame('2000-06-15 12:30:00', '2000-06-15 12:30:00');
    }
}

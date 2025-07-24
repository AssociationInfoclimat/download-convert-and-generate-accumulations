<?php

declare(strict_types=1);

namespace Infoclimat\Tiles\Tests\Integration;

require_once __ROOT__ . '/tiles.php';
require_once __ROOT__ . '/date.php';

use PHPUnit\Framework\TestCase;

use function Infoclimat\Tiles\get_last_tile_timestamp;
use function Infoclimat\Tiles\get_last_tile_update;
use function Infoclimat\Tiles\get_last_tiles_timestamps;
use function Infoclimat\Tiles\get_last_tiles_updates;

final class TilesTest extends TestCase
{
    public function testGetLastTilesUpdates(): void
    {
        $tiles = get_last_tiles_updates();
        $this->assertIsArray($tiles);
        foreach ($tiles as $key => $tile) {
            $this->assertIsString($key);
            $this->assertIsArray($tile);
        }
        $this->assertArrayHasKey('radaric', $tiles);
    }

    public function testGetLastTileUpdate(): void
    {
        $tile = get_last_tile_update('radaric');
        $this->assertIsArray($tile);
        $this->assertArrayHasKey('year', $tile);
        $this->assertArrayHasKey('month', $tile);
        $this->assertArrayHasKey('day', $tile);
        $this->assertArrayHasKey('hour', $tile);
        $this->assertArrayHasKey('minute', $tile);
    }

    public function testGetLastTilesTimestamps(): void
    {
        $timestamps = get_last_tiles_timestamps();
        $this->assertIsArray($timestamps);
        foreach ($timestamps as $key => $timestamp) {
            $this->assertIsString($key);
            $this->assertIsInt($timestamp);
        }
        $this->assertArrayHasKey('radaric', $timestamps);
    }

    public function testGetLastTileTimestamp(): void
    {
        $timestamp = get_last_tile_timestamp('radaric');
        $this->assertIsInt($timestamp);
        $this->assertLessThanOrEqual(60 * 60, time() - $timestamp, 'Last timestamp should be less than 1 hour ago');
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

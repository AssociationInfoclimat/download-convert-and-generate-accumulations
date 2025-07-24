<?php

declare(strict_types=1);

namespace Infoclimat\MeteoFrance\API\Tests\Integration;

require_once __ROOT__ . '/meteofrance-api.php';

use Exception;
use PHPUnit\Framework\TestCase;

use function Infoclimat\MeteoFrance\API\fetch_token;

final class MeteoFranceAPITest extends TestCase
{
    public function testFetchTokenThrowsIfMissingApplicationId(): void
    {
        $old = getenv('APPLICATION_ID');
        putenv('APPLICATION_ID'); // Unset
        $this->expectException(Exception::class);
        $this->expectExceptionMessage('Missing APPLICATION_ID in environment variables');
        fetch_token();
        if ($old !== false) {
            putenv("APPLICATION_ID={$old}");
        }
    }

    public function testFetchTokenReturnsTokenIfApplicationIdIsSet(): void
    {
        $applicationId = getenv('APPLICATION_ID');
        if (empty($applicationId)) {
            $this->markTestSkipped('APPLICATION_ID env var not set for integration test');
        }
        $token = fetch_token();
        $this->assertIsString($token);
        $this->assertNotEmpty($token);
        $this->assertGreaterThanOrEqual(30, strlen($token), 'Token length should be at least 30 characters');
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

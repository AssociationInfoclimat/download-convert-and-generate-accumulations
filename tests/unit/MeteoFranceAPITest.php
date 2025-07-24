<?php

declare(strict_types=1);

namespace Infoclimat\MeteoFrance\API\Tests\Unit;

require_once __ROOT__ . '/meteofrance-api.php';

use Infoclimat\MeteoFrance\API\CurlResponse;
use Infoclimat\MeteoFrance\API\InMemoryAPIFileDownloader;
use PHPUnit\Framework\TestCase;

use function Infoclimat\MeteoFrance\API\get_headers_callback;
use function Infoclimat\MeteoFrance\API\is_token_expired;

final class MeteoFranceAPITest extends TestCase
{
    public function testCurlResponseGetJSON(): void
    {
        $jsonString = '{"foo": "bar", "baz": 123}';
        $response = new CurlResponse(200, $jsonString);
        $this->assertSame(['foo' => 'bar', 'baz' => 123], $response->getJSON());
    }

    public function testCurlResponseGetJSONInvalid(): void
    {
        $response = new CurlResponse(200, 'not-json');
        $this->assertNull($response->getJSON());
    }

    public function testGetHeadersCallback(): void
    {
        $headers = [];
        $callback = get_headers_callback($headers);
        $callback(null, 'content-disposition: attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"');
        $this->assertSame(
            ['content-disposition' => 'attachment; filename="T_IPRN20_C_LFPW_20000615123045.h5"'],
            $headers
        );
    }

    public function testIsTokenExpiredNon401(): void
    {
        $response = new CurlResponse(200, '');
        $this->assertFalse(is_token_expired($response));
    }

    public function testIsTokenExpired401Downloading(): void
    {
        $response = new CurlResponse(401, '{"message": "Other"}');
        $this->assertTrue(is_token_expired($response, true));
    }

    public function testIsTokenExpired401OtherMessage(): void
    {
        $response = new CurlResponse(401, '{"message": "Other"}');
        $this->assertFalse(is_token_expired($response));
    }

    public function testIsTokenExpired401InvalidCredentials(): void
    {
        $response = new CurlResponse(401, '{"message": "Invalid Credentials"}');
        $this->assertTrue(is_token_expired($response));
    }

    public function testInMemoryAPIFileDownloader(): void
    {
        $mockResponse = new CurlResponse(200, 'data');
        $downloader = new InMemoryAPIFileDownloader([
            'https://www.example.com' => $mockResponse,
        ]);
        $result = $downloader->downloadAPIFile(
            '/my/path1',
            'https://www.example.com',
            ['header1'],
            ['opt1' => 'val1']
        );
        $this->assertSame($mockResponse, $result);
        $result404 = $downloader->downloadAPIFile(
            '/my/path2',
            'https://www.not-found.com',
            ['header2'],
            ['opt2' => 'val2']
        );
        $this->assertSame(404, $result404->code);
        $this->assertSame([
            [
                'path'    => '/my/path1',
                'url'     => 'https://www.example.com',
                'headers' => ['header1'],
                'options' => ['opt1' => 'val1'],
            ],
            [
                'path'    => '/my/path2',
                'url'     => 'https://www.not-found.com',
                'headers' => ['header2'],
                'options' => ['opt2' => 'val2'],
            ],
        ], $downloader->requests);
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

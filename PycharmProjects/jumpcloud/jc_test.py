#!/usr/bin/python

#
#  Author: Ted Power
#
#  Test Name: JumpCloud Hash Test
#
#  Description:
#  This test will test a hashing process' ability to receive a password and return a hash of
#  the password.  The server process is located on a hosted server and waits for password 'post'
#  to occur via HTTP.  The server will perform a SHA512/Base64 encoded hash and return the job-id/location
#  of the hash to the client.  The client must then issue a 'get' request via HTTP to retrieve the hash.
#
#  Server command input:
#  post: Issuing a post containing a password to /hash will direct the server to compute a hash for
#        password.  The server will respond with JSON content containing the status_code and job-id
#        of the hash, which specifies the location of the hash.
#  get:  Issuing a get containing the job-id to /hash will direct the server to retrieve the hash that
#        was previously computed for a password.
#  /stats: Issuing a get to /stats will direct the server to send a JSON response containing the
#          number of requests made and the mean time of a hash request in milliseconds.
#  shutdown: Issuing a post containing 'shutdown' will direct the server to shutdown the hash process.
#            The hash process will be restarted immediately by the host server.
#
#  Individual test cases are defined below as functions test1, test2, etc.


import threading
import requests
import json
import time

#  url of the test server to use for this test
url = 'http://radiant-gorge-83016.herokuapp.com'
urlh = url + '/hash'

pass_list1 = ['angrymonkey', 'guestpass', '457098', 'ThisPwIsLonger!@#$%', 'S0e1q2u3e4n5c6e7',
              'BlUe#SkY2dAy', '7thPasswordInTheList', 'asdfklje8238k23adj', '789yikl678_@#', 'sdf"']
pass_list2 = ['2ndpassw', 'darknite', 'iforgot']


#  Thread class to use for simultaneous sending of password posts
class MyThread (threading.Thread):
    def __init__(self, thread_id, pwd):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = pwd
        self.pswd = pwd
        self.failed = False
        self.jobid = None
        self.timer = 0

    #  Runs with the thread is 'started' via a thread.start
    def run(self):
        print 'Starting thread:', self.name
        self.jobid, self.timer = push_passwd(self.name, self.pswd)
        if not self.jobid:
            self.failed = True
        print 'Exiting thread: %s\n' % self.name


#  push_passwd(thread_name, pwd)
#  Called by the thread-run to push a password to the server
#  Input: thread name, password to hash
#  Return: job-id returned from the server, time to process push request
def push_passwd(thread_name, pwd):
    post_data = {"password": pwd}
    started = time.time()
    post_response = requests.post(urlh, data=json.dumps(post_data))
    timer = time.time() - started
    if post_response.status_code == 200:
        print 'Post Passwd: %s Jobid:%s Status code:%s ' % (thread_name, post_response.text,
                                                            post_response.status_code)
        if post_response.text == '1':
            print 'Server Restarted'
        return post_response.text, timer
    else:
        print 'Post failed:%s status_code:%s' % (pwd, post_response.status_code)
        return None, None


#  get_hash_values(job_ids)
#    Get hash values for job-id's stored in a dictionary by issuing a HTTP get request.
#    Input: Dictionary containing the key/value pairs for a password and job-id for the
#           hash value.
#    Output: Response and dictionary.
#            Response is True if a failure occurred while trying to retrieve a hash
#            False if the hash gets were successful.
#            Dictionary (hashd) with key/value pair of the password and hash value
def get_hash_values(job_ids):
    failed = False
    hashd = {}
    for pwd, hash_loc in job_ids.iteritems():
        urlhg = urlh + '/' + hash_loc
        print 'Passwd: %s, %s' % (pwd, urlhg)
        get_response = requests.get(urlhg)
        if get_response.status_code == 200:
            hashd[pwd] = get_response.text
        else:
            print 'No hash value returned:%s Return code:%s' % (pwd, get_response.status_code)
            failed = True
    return failed, hashd


#  exec_threads(pwd_list)
#  Execute a separate thread for each of the passwords in the list.
#  This tests simultaneous processing of requests by the server process.
#  Input: list of passwords
#  Return: list of thread objects
def exec_threads(pwd_list):
    thrd_list = []
    th_num = 0
    for passwd in pwd_list:
        th_num += 1
        # Create a new thread and add it to a thread list
        thread = MyThread(th_num, passwd)
        thrd_list.append(thread)
        # Start new thread
        thread.start()
    return thrd_list


#  get_stats()
#  Get current stats from the server via an HTTP get request.
#  Input: None
#  Returns: True if the stats request was rejected by the server
#           False if the stats request was successful.
def get_stats():
    urls = url + '/stats'
    get_response = requests.get(urls)
    if get_response.status_code == 200:
        print 'Stats:', get_response.text, get_response.status_code
        return False
    else:
        print 'Stats failed'
        return True


#  shutdown()
#  Issue a shutdown to the server via an HTTP post.
#  Input: None
#  Returns: True if the shutdown was rejected by the server
#           False if the shutdown was accepted.
def shutdown():
    print 'Sending shutdown'
    post_response = requests.post(urlh, data='shutdown')
    if post_response.status_code == 200:
        print 'Shutdown issued'
        return False
    else:
        print 'Shutdown failed'
        return True


#  exec_test(test_name, wait_limit)
#  The exec_test function takes the name of the test function (testcase)
#  and executes it after checking to see if the server is responding.
#  This deals with a problem where the server goes dark for a period of
#  10 - 30 minutes by waiting until the server is up and running before
#  executing the test.
#  Input: test name, wait_limit - maximum time to wait for server process
#  Returns: True if wait_limit was exceeded
#           False if test was executed
def exec_test(test_name, wait_limit):
    slp_time = 30
    tot_time = 0
    print 'Checking server availability'
    print 'Waiting to start:', test_name
    while tot_time < wait_limit:
        # Check for stats to see if the server is available
        if not get_stats():
            break
        time.sleep(slp_time)
        tot_time += slp_time
        if not tot_time % 60:
            mins = tot_time / 60
            print '    Elapsed time:%d min' % mins
    if tot_time >= wait_limit:
        print 'Maximum server wait time exceeded'
        return True
    else:
        rslt = test_name()
        if rslt:
            print '%s FAILED to execute' % test_name
            return True
        else:
            return False


#  thread_wait(t_list)
#  Wait for threads to exit and then put the job-id into a dictionary.
#  Input: Takes a list(t_list) of thread objects.  Each thread object
#  will be waited on for it to exit.
#  Returns: response indicating failure if True and a job-id dictionary
#  with the password key and job-id value.
def thread_wait(t_list):
    job_ids = {}
    failed = False
    for t in t_list:
        t.join()
        if t.failed:
            failed = True
        else:
            job_ids[t.pswd] = t.jobid
    return failed, job_ids


#  hash_pwd(pwd)
#  Perform a sha512 hash and base64 encode it
#  Input: password string
#  Return: base64 encoded sha512 password
def hash_pwd(pwd):
    from base64 import b64encode
    from hashlib import sha512
    return b64encode(sha512(pwd).digest())


#  TEST CASE DEFINITIONS
#  Test-1 will issue a shutdown and then check to see if the server process
#  restarts immediately.  If the job-id for the next push is '1' then we
#  know the server restarted.
def test1():
    print '\nTest1: Start'
    failed = False
    #  Send out a few password posts to ensure that server memory contains
    #  a few job IDs.
    thrd_list = exec_threads(pass_list2)
    resp, job_ids = thread_wait(thrd_list)
    if resp:
        failed = True
    #  Now shutdown the server and give a some time to restart
    if shutdown():
        failed = True
    else:
        wait_fail = False
        thrd_list2 = []
        for i in range(2):
            time.sleep(30)
            thrd_list2 = exec_threads(['junkPass'])
            resp, job_ids = thread_wait(thrd_list2)
            if resp:
                wait_fail = True
            else:
                wait_fail = False
                break
        if wait_fail:
            failed = True
        else:
            if thrd_list2[0].jobid == '1':
                print 'Server process successfully restarted'
            else:
                failed = True
                print 'Server process was not restarted'
    if failed:
        print 'Test1: FAILED\n'
    else:
        print 'Test1: PASSED\n'


#  Test-2 - Post a bunch of passwords to hash but don't retrieve the hashes.
#  This tests whether they can be received by the server simultaneously
#  and if the server can handle a large number of requests.
#  check to see if the timer is less than 5 sec, meaning the server didn't
#  wait to process the password post.  This delay is necessary to ensure that
#  the requests are queued before being processed.
def test2():
    print '\nTest2: Start'
    iterator = 100
    failed = False
    thrd_master = []
    #  Start a thread for each password in pass_list1 * iterator
    for idx in range(iterator):
        thrd_list = exec_threads(pass_list1)
        thrd_master.extend(thrd_list)
    if get_stats():
        failed = True
    # Wait for the threads to end
    for t in thrd_master:
        t.join()
        if t.failed:
            print 'Thread %s failed' % t.pswd
            failed = True
        elif t.timer and t.timer < 5:
            print 'Post time was less than 5 seconds:', t.timer
            failed = True
    if get_stats():
        failed = True
    if shutdown():
        failed = True
    if failed:
        print 'Test2: FAILED\n'
    else:
        print 'Test2: PASSED\n'


#  Test-3 - Ensure that a list of passwords can accept simultaneous posts and
#  retrieve the hash after getting all of the responses from the posts.  This
#  tests that the client can get all of the hashes it requested without any
#  errors.
def test3():
    print '\nTest3: Start'
    failed = False
    # Create threads with the first list of passwords
    thrd_list = exec_threads(pass_list1)
    if get_stats():
        failed = True
    # Wait for the threads to end
    resp, job_ids = thread_wait(thrd_list)
    if resp:
        failed = True
    resp, hashd = get_hash_values(job_ids)
    if resp:
        failed = True
    for pwd, hashv in hashd.iteritems():
        print 'Password:', pwd
        print '    Hash:', hashv
    if shutdown():
        failed = True
    if failed:
        print 'Test3: FAILED\n'
        return True
    else:
        print 'Test3: PASSED\n'
        return False


#  Test-4 - Get a list of passwords, issue a shutdown, then get a new set of passwords.
#  This tests whether the server processes all pending posts but rejects posts after a
#  shutdown.
def test4():
    print '\nTest4: Start'
    failed_step1 = False
    failed_step2 = False
    # Create threads with the first list of passwords
    thrd_list = exec_threads(pass_list1)
    if get_stats():
        failed_step1 = True
    if shutdown():
        failed_step1 = True
    # Wait for the threads to end
    resp, job_ids = thread_wait(thrd_list)
    if resp:
        failed_step1 = True
    elif len(job_ids) < len(pass_list1):
        print 'All posts did not complete.'
        print '%d completed but expected %d' % (len(job_ids), len(pass_list1))
        failed_step1 = True
    num_jobid = len(job_ids)

    # Execute new set of threads.  These passwords should be rejected because of the previous shutdown.
    thrd_list2 = exec_threads(pass_list2)
    # Wait for the threads to end
    resp, job_ids2 = thread_wait(thrd_list2)
    if resp:
        failed_step2 = True
        #  See if the jobid is greater than the number from the last pass_list.  If so, then
        #  the server did not restart, which would have restarted the numbers at 1.
    for thrd in thrd_list2:
        if thrd.jobid > num_jobid:
            failed_step2 = True
            print 'The job IDs after the shutdown are greater than expected, indicating server did not restart'
            print 'Expected: job-id 1, Received: %d' % thrd.jobid
    if not failed_step2:
        resp, hashd = get_hash_values(job_ids)
        if resp:
            failed_step2 = True
        else:
            for pwd, hashv in hashd.iteritems():
                print 'Password: %s' % pwd
                print '    Hash: %s' % hashv
    #  This is a negative test so when it can't post passwords it passes.
    if failed_step1:
        print 'Test4: FAILED\n'
        return True
    elif failed_step2:
        print 'Test4: PASSED\n'
        return False
    else:
        print 'Test4: FAILED\n'
        return True


#  Test-5 - Pass a set of passwords to be hashed and retrieve the hash values.
#  These values will be compared against a local hash of the same password to
#  validate sha512/base64 encoding was used by the server.
def test5():
    print '\nTest5: Start'
    failed = False
    # Create threads with the first list of passwords
    thrd_list = exec_threads(pass_list1)
    if get_stats():
        failed = True
    # Wait for the threads to end
    resp, job_ids = thread_wait(thrd_list)
    if resp:
        failed = True
    resp, hashd = get_hash_values(job_ids)
    if resp:
        failed = True
    for pwd, rhash in hashd.iteritems():
        myhash = hash_pwd(pwd)
        if rhash == myhash:
            print 'Password:', pwd
            print '    Hash:%s\n' % rhash
        else:
            print 'Hash mismatch between computed and retrieved hashes:', pwd
            print 'Computed: %s' % myhash
            print 'Retrieved: %s\n' % rhash
            failed = True
    if failed:
        print 'Test5: FAILED\n'
        return True
    else:
        print 'Test5: PASSED\n'
        return False


def main():
    isfailed = False
    #  Test-1
    if exec_test(test1, 1800):  # Wait up to 30 min
        isfailed = True
    #  Test-2
    if exec_test(test2, 1800):
        isfailed = True
    #  Test-3
    if exec_test(test3, 1800):
        isfailed = True
    #  Test-4
    if exec_test(test4, 1800):
        isfailed = True
    #  Test-5
    if exec_test(test5, 1800):
        isfailed = True

    if isfailed:
        return 1
    else:
        return 0


if __name__ == '__main__':
    ret = main()
    exit(ret)
